# Plan: Fix homesrv cron GPU1-busy fallback

## Phase 0 — Read-only recon (no code changes)

Resolve the absolute path first, then inspect. Do this from the repo, never from /tmp:

1. `echo ~` → confirm the absolute repo path (e.g. `/home/alex/coding-projects/model-hub`).
2. `ls ~/coding-projects/model-hub` and read, in this order:
   - `README.md` / `docs/` — how the repo is deployed (is the cron script, llama-swap config, and cron entry all tracked here, or is the box drifted from the repo?)
   - the homesrv cron entry: `crontab -l` (and any `cron/`, `systemd/`, or `deploy/` dir in the repo) to find the exact 4-hourly line and what script it invokes
   - the homesrv script itself (likely `scripts/homesrv*` or similar) — find where the model is chosen and where the 500 "exited prematurely" originates
   - the llama-swap config in the repo (`llama-swap*.yaml`, docker-compose, or systemd unit) — find how `qwen3.8-27b-abliterated-gpu0` is registered and whether the config supports a fallback/retry chain or whether the fallback must live in the cron wrapper
   - any existing fallback/retry logic and the router's live state: `curl http://100.101.1.10:8080/v1/models` (read-only) to confirm `qwen3.8-27b-abliterated-gpu0` is registered and see the primary model's name
3. Confirm the failure mode: check cron/router logs and `nvidia-smi` / ComfyUI processes to see GPU1 held.

Output of Phase 0: a one-paragraph map of where the fallback belongs (cron wrapper vs. llama-swap config) and the exact file list.

## Phase 1 — Exactly one `claude -p` call

**Workdir:** the absolute repo path, resolved in Phase 0. Do **not** rely on the harness default cwd.

```bash
cd /home/alex/coding-projects/model-hub && claude -p '<prompt>'
```

The prompt must be self-contained and absolute-path-explicit, e.g.:

> Work only in /home/alex/coding-projects/model-hub (absolute path). Read the homesrv cron script and llama-swap config. Implement a fallback so that when the GPU1-bound primary model fails (llama-swap 500 "exited prematurely", e.g. because ComfyUI holds GPU1), the cron falls back to qwen3.8-27b-abliterated-gpu0. Keep changes minimal and in the repo; do not edit files outside the repo, do not commit, do not restart or reload the live llama-swap or cron on the box — report what deploy step would be needed. Print the absolute path of every file you create or modify.

If the single call fails or produces no changes, stop and report — do not retry with a second code-changing call.

## Phase 2 — Verification (read-only, absolute paths only)

1. **Provenance check (the trap):** `git -C /home/alex/coding-projects/model-hub status --porcelain` and `git -C ... diff --stat`. Confirm: only the intended files changed, nothing landed in /tmp (`ls /tmp` for stray repo files), and the changed files are the ones claude reported.
2. **Read the changed files** at their absolute paths and confirm the fallback logic is actually present and correct (primary → on failure → GPU0 fallback; no silent swallow of errors).
3. **Run the project's checks** — whatever the repo defines (`make test` / `npm test` / `pytest` / lint; check README/Makefile first).
4. **Functional proof:**
   - With ComfyUI holding GPU1 (confirm via `nvidia-smi`), run the homesrv cron entry exactly as cron would (or `bash <absolute path to script>`). Expect: exit 0, and the response served by `qwen3.8-27b-abliterated-gpu0` — verify via the router's log/response and the script's output.
   - Also sanity-check the primary path when GPU1 is free (or note it couldn't be tested).
   - Capture the before/after evidence: the 500 with GPU1 busy (from logs) vs. the 200/fallback success after the fix.

## Phase 3 — Report to Alex

- What changed (file list + one-line summary each), the exact diff stat.
- The proof: before/after behavior, which model served, cron exit code, check results.
- Caveats: whether the fix requires a reload/restart of llama-swap or a cron reinstall (do not do this silently — flag it for Alex); whether the primary path was verified; anything that couldn't be tested.

## How I prevent the "Claude ran in /tmp" trap

- The `claude -p` invocation **starts with `cd` to the literal absolute repo path** (resolved in Phase 0), never the harness default cwd.
- The prompt contains the absolute repo path and instructs claude to print absolute paths of everything it touches — so any out-of-repo edit is visible in its output.
- All verification reads and git commands use `git -C <absolute path>` / absolute file paths, never relative paths from the shell's cwd.
- After the call I run `git -C <absolute path> status --porcelain` **and** a /tmp sweep, so a /tmp-landed change is caught immediately rather than "lost" — and I never trust the shell's cwd as evidence.

One honesty note: the "prove it works" claim is only as strong as the functional test in Phase 2. If ComfyUI can't be held on GPU1 during verification, I'll say so and report the code-level proof plus whatever partial evidence exists, rather than claim a green run I didn't see.