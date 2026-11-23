I’ll treat the repo path as the single source of truth and make Claude’s cwd and my verification cwd identical before and after the edit. I will not hand-edit code; only one `claude -p` invocation will make changes.

## 1. First: resolve the repo and inspect read-only

I will first run:

```bash
REPO_ABS="$(realpath ~/coding-projects/model-hub)"
printf 'REPO_ABS=%s\n' "$REPO_ABS"
cd "$REPO_ABS"
pwd -P
```

Then I’ll locate the cron entrypoint and fallback logic:

```bash
find "$REPO_ABS" -maxdepth 3 -type f \
  \( -name '*homesrv*' -o -name '*cron*' -o -name '*llama*' -o -name '*test*' \) \
  | sort
```

Files I will read first, in this order:

1. The discovered cron entrypoint, likely `cron/homesrv.sh` or `scripts/homesrv.*`.
2. The llama-swap/router config/model registry, likely `llama-swap/config.yaml`, `config.yaml`, or `models.yaml`.
3. The test/check setup: `Makefile`, `package.json`, `pyproject.toml`, and any `tests/test_homesrv*` file.
4. `README.md` / cron docs to confirm the canonical test command and expected fallback behavior.

I’ll use `read_file` with absolute paths only, e.g.:

```bash
read_file "$REPO_ABS/cron/homesrv.sh"
read_file "$REPO_ABS/config.yaml"
read_file "$REPO_ABS/tests/test_homesrv.py"
```

If filenames differ, I’ll use the `find` results and read the actual discovered files.

## 2. The exact one `claude -p` invocation

After inspection, I will run exactly one `claude -p` call. The shell cwd is set to the resolved repo absolute path, and the prompt repeats that absolute path. I will capture output into a repo-scoped log so it cannot be “lost” in `/tmp`.

```bash
REPO_ABS="$(realpath ~/coding-projects/model-hub)"
cd "$REPO_ABS" || exit 1
[ "$(pwd -P)" = "$REPO_ABS" ] || exit 1

claude -p 'Work only in /home/alex/coding-projects/model-hub. Use the absolute repo path given here; do not use /tmp or any other directory. Read the 4-hourly homesrv cron entrypoint and its llama-swap fallback logic, plus the project test/check files. Fix the cron fallback so that when GPU1 is busy or the primary GPU1 model returns HTTP 500 with "exited prematurely", homesrv retries with the model `qwen3.8-27b-abliterated-gpu0` instead of failing. Preserve existing behavior for unrelated errors. Add or update a focused test that simulates GPU1 busy/500 and asserts the fallback request uses exactly `qwen3.8-27b-abliterated-gpu0`. Run the project checks and the focused test; fix any failures within this same invocation. Do not edit files outside the repo. At the end, report changed files, test commands/results, and confirm `pwd` was the repo path.' \
  --permission-mode acceptEdits \
  --allowedTools Read Edit Write Bash Grep Glob \
  --max-turns 25 \
  --output-format json \
  | tee "$REPO_ABS/.claude-homesrv-run.json"
```

Note: if Alex’s `$HOME` is not `/home/alex`, I will substitute the resolved `$REPO_ABS` literal in the prompt and command. The key is that the shell cwd is explicitly the resolved repo absolute path, and Claude is told to use that same absolute path.

## 3. Verification after the single Claude call

I will verify from the repo root using absolute paths, not `/tmp`:

1. Confirm Claude changed files in the repo:

```bash
cd "$REPO_ABS"
git status --short
git diff --stat
git diff --name-only
```

2. Read the changed files with absolute paths:

```bash
read_file "$REPO_ABS/cron/homesrv.sh"
read_file "$REPO_ABS/tests/test_homesrv.py"
```

I’ll check that:
- the fallback condition handles GPU1 busy / HTTP 500 `exited prematurely`;
- the fallback model string is exactly `qwen3.8-27b-abliterated-gpu0`;
- the test simulates the 500 and asserts that model;
- unrelated error handling is preserved.

3. Run the project’s canonical checks from the repo root. I’ll determine the exact command from the repo files, e.g.:

```bash
cd "$REPO_ABS"
make test
```

or, if the repo uses Python/Node:

```bash
cd "$REPO_ABS"
pytest -q
# or
npm test
```

4. Run the focused fallback test explicitly, e.g.:

```bash
cd "$REPO_ABS"
pytest -q tests/test_homesrv.py -k fallback
```

or the equivalent test command discovered from the repo. This test is the proof: it injects a GPU1-busy / 500 `exited prematurely` response and asserts the cron retries with `qwen3.8-27b-abliterated-gpu0`.

5. Verify no edits escaped the repo:

```bash
cd "$REPO_ABS"
git diff --name-only | awk -v r="$REPO_ABS/" 'BEGIN{ok=1} { if ($0 !~ "^"r) ok=0 } END{exit !ok}'
```

If the repo diff is empty or changes appear outside `$REPO_ABS`, I’ll treat the run as failed rather than “looking elsewhere” for output.

## 4. How I prevent the `/tmp` trap

I will:
- Resolve `REPO_ABS="$(realpath ~/coding-projects/model-hub)"` once.
- `cd "$REPO_ABS"` before invoking Claude, and assert `pwd -P` equals `$REPO_ABS`.
- Put the absolute repo path explicitly in the Claude prompt and forbid `/tmp`.
- Capture Claude’s output into `$REPO_ABS/.claude-homesrv-run.json`, not `/tmp`.
- Verify with `git -C "$REPO_ABS"` and `read_file "$REPO_ABS/..."` absolute paths.
- Treat an empty repo diff as a failed edit, not as “maybe it edited somewhere else.”

## 5. What I will report to Alex

I’ll report:

- **Root cause:** the cron fallback did not handle GPU1-busy / HTTP 500 `exited prematurely`, or pointed at the wrong fallback model.
- **Fix:** when GPU1 is busy or returns that 500, homesrv now retries with `qwen3.8-27b-abliterated-gpu0`.
- **Files changed:** exact paths from `git diff --name-only`.
- **Proof:** the focused test name/command and its passing output, showing a simulated GPU1 500 causes a request using `qwen3.8-27b-abliterated-gpu0`; plus the full project check result.
- **Process compliance:** exactly one `claude -p` call was used, with an explicit absolute repo workdir; no manual code edits.
- **Trap prevention:** repo path resolved, cwd asserted, output captured under the repo, and verification done with absolute repo paths.