As Hermes director, I will not hand-edit code. All code changes go through exactly one `claude -p` call, from the correct workdir, then I verify.

### 1. Recon - read-only first

From terminal, resolve the repo to an absolute path and inventory it before any delegation:

```bash
REPO=$(realpath ~/coding-projects/model-hub); echo $REPO; cd "$REPO"; pwd; ls -la
crontab -l; ls -la /etc/cron.d/ 2>/dev/null; systemctl list-timers --all 2>/dev/null | grep -i homesrv
nvidia-smi; curl -s http://100.101.1.10:8080/v1/models | head -c 2000
grep -rn "homesrv\|exited prematurely\|gpu1\|GPU1\|qwen3" --include="*.py" --include="*.sh" --include="*.md" --include="*.yaml" --include="*.yml" --include="*.toml" --include="*.json" . | head -n 200
find . -iname "*homesrv*" -o -iname "*cron*" -o -name "README*" -o -name "CLAUDE.md" -o -name "AGENTS.md" | head -n 100
```

Files I will read first with `read_file` (paths confirmed by the above):
- `~/coding-projects/model-hub/README.md`, `CLAUDE.md`/`AGENTS.md` if present - project checks, conventions
- The cron definition itself: crontab entry / `cron/*` / systemd timer pointing to the 4-hourly job
- The homesrv script/module it invokes, e.g. `scripts/homesrv*` or `src/homesrv/*`
- llama-swap config, e.g. `llama-swap.yaml` - to confirm exact model ID `qwen3.8-27b-abliterated-gpu0` and router endpoint `http://100.101.1.10:8080`
- Existing tests for homesrv, e.g. `tests/test_*homesrv*`

Goal of recon: find where the primary model is chosen, where the 500 `exited prematurely` from llama-swap is (not) handled, and how GPU1-busy is currently detected (if at all).

### 2. The single delegated code change

Exactly one invocation, with explicit absolute workdir enforced by `cd` + `pwd` in the same shell before invoking Claude. Claude Code's workdir is its cwd, so this is the workdir control:

```bash
REPO=$(realpath ~/coding-projects/model-hub); cd "$REPO"; pwd; git status --short
claude -p "In this repository only ($REPO), fix the 4-hourly homesrv cron failure: when the primary model returns HTTP 500 'exited prematurely' from the llama-swap router at http://100.101.1.10:8080 because ComfyUI holds GPU1, fall back once to model qwen3.8-27b-abliterated-gpu0 on GPU0. Detect GPU1-busy / primary-500, log the fallback reason clearly, retry only once with the gpu0 model, do not kill ComfyUI or any GPU process, and preserve existing behavior when GPU1 is free. Add or update tests covering: (1) primary succeeds - no fallback, (2) primary 500 exited prematurely - falls back to qwen3.8-27b-abliterated-gpu0 and succeeds, (3) fallback also fails - clear error, non-zero exit. Do not create final files outside this repo (no /tmp output). Run the project's checks and report files changed."
```

No `patch` tool use by me. If this call fails, I stop and report to Alex - I do not hand-edit as a workaround.

**Trap prevention (the previous /tmp loss):** The prior session failed because Claude ran in `/tmp` while verification looked in `~/coding-projects/model-hub`. I prevent recurrence by: (a) resolving `REPO` to an absolute path and `cd`-ing there in the same command that launches `claude -p`, (b) printing `pwd` and `git status` immediately before the call so the workdir is on record, (c) instructing Claude in-prompt that the repo is the only valid output location, and (d) verifying afterward in that same `$REPO` directory with `git status`/`git diff` - any Claude output claimed in `/tmp` is treated as lost/invalid, not as the deliverable.

### 3. Verification (by me, read-only + checks)

In `$REPO` only:
```bash
cd "$REPO"; pwd; git status --short; git diff
```
- `read_file` every file listed in `git diff` to confirm the fallback logic, single-retry bound, and logging.
- Run the project's own checks discovered in recon (e.g. `pytest -q`, `npm test`, `shellcheck`, Makefile target - whatever README specifies), in `$REPO`.

### 4. Prove it works

1. Confirm the fallback model exists on the router: `curl -s http://100.101.1.10:8080/v1/models | grep qwen3.8-27b-abliterated-gpu0`
2. Unit/integration test with a mocked primary 500 - must show fallback selection.
3. Live proof: run the homesrv job once manually (same command the cron uses) while GPU1 is busy / primary would 500 - capture exit code and log line showing `GPU1 busy -> falling back to qwen3.8-27b-abliterated-gpu0` and a successful (200) completion instead of the previous 500.

### 5. Report to Alex

Concise summary: root cause (no fallback on llama-swap 500 when ComfyUI holds GPU1), the exact file(s)/diff changed via the single `claude -p` call, test/check output, the live manual-run log proving fallback to `qwen3.8-27b-abliterated-gpu0`, next scheduled cron time, and rollback (`git diff` revert) if needed.