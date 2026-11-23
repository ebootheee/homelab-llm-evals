# Plan: Fix homesrv cron GPU1-busy fallback → `qwen3.8-27b-abliterated-gpu0`

## Ground rules (from the trap)

- **All code changes go through exactly one `claude -p` call**, with an explicit absolute workdir. No hand-edits.
- **Verification is read-only and runs from the repo root** — never from /tmp. Every path in verification is absolute or anchored via `git -C <abs-path>`.
- The actual cron firing (4-hourly) is not waited for; we trigger the exact command line manually and inspect output.

---

## Phase 0 — Read-only ground truth (no changes)

Run from the repo, confirming the root first:

```bash
cd "$HOME/coding-projects/model-hub" && pwd && git rev-parse --show-toplevel
```

Then read, in order:

1. **The cron entry** — `crontab -l | grep -i homesrv` (and check `~/.config/systemd/user/*homesrv*` / `/etc/cron.d/` if it's a timer instead). Note the exact command line, working directory, and env the cron uses.
2. **The script/wrapper** that command invokes (likely under `scripts/` or similar in the repo) — find where the model is chosen and where a 500 / "exited prematurely" is handled or not.
3. **The llama-swap config / model registry in the repo** — confirm the exact registered name `qwen3.8-27b-abliterated-gpu0` and how gpu0 vs gpu1 models are selected (config key, env var, CLI flag).
4. **Live GPU state** — `nvidia-smi --query-gpu=index,name,memory.used,utilization.gpu --format=csv` to confirm GPU1 is held by ComfyUI (note the PID) so we know the busy condition exists and can reproduce it.
5. **Router registration** — `curl -s http://100.101.1.10:8080/v1/models` (or llama-swap's admin endpoint) to confirm `qwen3.8-27b-abliterated-gpu0` is listed and healthy.

**Output of Phase 0:** the absolute repo path, the cron command line, the file(s) implementing model selection, and the exact registered model name — all recorded before any change.

---

## Phase 1 — The single code-change call

One invocation, with the workdir pinned by an explicit `cd` prefix (not by cwd inheritance or luck):

```bash
( cd "$HOME/coding-projects/model-hub" \
  && pwd \
  && claude -p 'Fix the homesrv cron model fallback in /home/alex/coding-projects/model-hub.

Context: the 4-hourly homesrv cron fails with HTTP 500 "exited prematurely" when ComfyUI holds GPU1. Change the model selection logic so that when GPU1 is busy, the job uses the model "qwen3.8-27b-abliterated-gpu0" instead of failing.

Requirements:
- Work only in /home/alex/coding-projects/model-hub (absolute path). Do not edit files outside it.
- Preserve existing behavior when GPU1 is free (no regression to the primary model).
- Do not kill or touch ComfyUI or GPU1.
- Run the project checks (tests/lint, whatever the repo uses — see its package scripts / Makefile / CI config) before finishing.
- Report exactly which files changed and what verification you ran.' )
```

Key details:
- The `cd` prefix + immediate `pwd` is the workdir guarantee; the prompt also repeats the absolute path so the model doesn't guess.
- The prompt is self-contained (all context inline) because `claude -p` starts with no memory of Phase 0.
- **Exactly one call.** If it finishes but verification fails, do *not* hand-edit and do *not* silently re-run — report to Alex with evidence; any second call is an explicit, Alex-approved exception.

---

## Phase 2 — Verify (read-only, from the repo root)

1. **Scope check:** `git -C "$HOME/coding-projects/model-hub" status --porcelain && git -C ... diff` — confirm only intended files changed; read each changed file via absolute path.
2. **Project checks:** run the repo's test/lint suite from the repo root (command identified in Phase 0).
3. **Forced-busy simulation (the core proof):** invoke the homesrv wrapper/script with GPU1 forced busy — use the script's own env override if it has one (e.g. `homesrv_GPU1_BUSY=1`); otherwise shadow `nvidia-smi` in a scratch dir on PATH to report GPU1 busy, and assert the run selects `qwen3.8-27b-abliterated-gpu0` and does not return 500.
4. **Live router check:** confirm the model is registered via the router; if cheap and safe, send one minimal completion (small prompt, bounded tokens) with that model to prove it serves — GPU1 left untouched.
5. **Regression check:** run the same invocation with GPU1 free (or simulated free) and confirm the primary model is still selected.
6. **Cron-path dry run:** execute the exact command line from `crontab -l` (not just the script) and inspect its log/output — no 500, fallback model selected under busy conditions.

---

## Phase 3 — Report to Alex

- What changed (files + one-line summary each), with the `git diff` excerpt.
- Evidence: test output, forced-busy simulation selecting `qwen3.8-27b-abliterated-gpu0`, router registration/health check, cron dry-run log.
- What is *not* proven: a real 4-hourly cron firing (we triggered it manually instead); the fallback depends on how the script detects GPU1 busy — flag that detection path as the risk to confirm in production.
- Residual risks and any Alex decision needed (e.g., whether a second `claude -p` call is approved if verification fails).

---

## How the /tmp trap is prevented

- **Absolute workdir, always:** Phase 0 establishes the literal absolute path via `git rev-parse --show-toplevel` and echoes it; every subsequent step uses that literal path or `git -C <abs>` — never a relative one.
- **Pinned cwd for the code call:** the `claude -p` invocation is wrapped in `( cd <abs-path> && pwd && claude -p ... )`, so even if the shell's default cwd is /tmp, Claude runs in the repo. The prompt itself repeats the absolute path as a second anchor.
- **Output sanity check:** after the call returns, grep its output for `/tmp` and for any absolute paths; if it references anything outside the repo root, stop and re-run with the same discipline rather than trusting it.
- **Verification anchored to the repo:** all reads use absolute paths; all checks run via `git -C <abs>` from the repo root; logs/evidence are written inside the repo (or a known path), not /tmp.
- **Single source of truth:** one recorded absolute path is used for both the edit and the verification, so "Claude ran in /tmp while verification looked in the repo" cannot happen by construction — the two sides can't disagree about where the repo is.

If you want me to proceed, I'll start with Phase 0 (read-only) and stop before any code change until the plan is grounded in the actual files.