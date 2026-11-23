Here is the full plan to fix the `homesrv` cron fallback logic on Alex's box.

### 1. Context & Strategy
*   **Environment:** `~/coding-projects/model-hub` (Absolute path: `/home/alex/coding-projects/model-hub`).
*   **Problem:** The 4-hourly cron job fails with HTTP 500 "exited prematurely" because it attempts to use a model on GPU1, which is occupied by ComfyUI.
*   **Goal:** Implement a fallback mechanism in the routing logic (or the specific script invoked by the cron) such that if GPU1 is busy/unavailable, it defaults to `qwen3.8-27b-abliterated-gpu0`.
*   **Constraint:** I must NOT hand-edit code. I will use exactly one `claude -p` invocation with an explicit workdir.

### 2. Step-by-Step Execution Plan

#### Phase 1: Reconnaissance (Read-Only)
Before invoking Claude, I need to understand the current architecture to write a precise prompt. I will read the following files in `~/coding-projects/model-hub`:
1.  **Cron Definition:** Check `/etc/cron.d/homesrv` or `crontab -l` output (via terminal) to see exactly which script is being called and with what arguments.
2.  **Entry Point Script:** Identify the main Python/Shell script executed by the cron (e.g., `homesrv.py`, `run_homesrv.sh`, or `main.py`). Read this file to understand how it currently selects the model/GPU.
3.  **Router Client Logic:** Find the module that interacts with the `llama-swap` router at `http://100.101.1.10:8080`. This is likely a utility file (e.g., `router_client.py`, `api.py`). I need to see how it currently handles errors or GPU selection.
4.  **Configuration:** Check for any `.env` files, `config.yaml`, or hardcoded constants defining the default model and GPU assignments.

*Goal of Phase 1:* Determine where the "GPU1 busy" check happens (or where it *should* happen) and where the model name is defined.

#### Phase 2: Code Modification (Single `claude -p` Call)
I will construct a single, explicit prompt for Claude Code. The prompt will instruct it to modify the relevant files in the repository to add fallback logic.

**The `claude -p` Invocation:**
```bash
cd /home/alex/coding-projects/model-hub && claude -p "
Context:
You are working in the model-hub repository at /home/alex/coding-projects/model-hub.
The system has two GPUs. GPU1 is often busy with ComfyUI.
The cron job 'homesrv' currently fails with HTTP 500 'exited prematurely' when it tries to use a model on GPU1 while it is busy.

Task:
Modify the code so that if the primary model (currently on GPU1) is unavailable or the request fails due to GPU contention, the system automatically falls back to the model 'qwen3.8-27b-abliterated-gpu0'.

Requirements:
1. Identify the file(s) responsible for model selection or API interaction with the llama-swap router (http://100.101.1.10:8080).
2. Implement a try/except or status-check logic around the primary model call.
3. If the primary model fails (specifically if it indicates GPU unavailability or a 500 error related to exit), retry the request using the model name 'qwen3.8-27b-abliterated-gpu0'.
4. Ensure the fallback model is correctly mapped to GPU0 in the request payload if applicable.
5. Do not change the primary model unless it fails.
6. Add a log message indicating when the fallback is triggered (e.g., 'Falling back to qwen3.8-27b-abliterated-gpu0 because GPU1 is busy').

Files to inspect/modify:
[Insert list of specific files found in Phase 1, e.g., src/router.py, scripts/homesrv.py]

Please make the necessary code changes directly in the working directory.
"
```
*(Note: I will replace `[Insert list...]` with the actual file paths identified in Phase 1.)*

#### Phase 3: Verification (Read-Only + Execution)
After Claude finishes, I will verify the changes without editing them myself.

1.  **Read Changed Files:** Use `read_file` to inspect the files Claude modified. Look for:
    *   The new fallback logic (`try/except` or conditional check).
    *   The string `'qwen3.8-27b-abliterated-gpu0'`.
    *   Proper error handling that catches the specific "exited prematurely" or 500 error.
2.  **Run Project Checks:**
    *   Execute any existing unit tests: `pytest` (or `python -m unittest`).
    *   Run linting/type checking if configured (e.g., `flake8`, `mypy`, `ruff`).
    *   **Dry Run Simulation:** If possible, run the specific cron script in a "dry-run" mode or with a debug flag to see if it attempts the primary model first and logs the fallback logic. If no dry-run exists, I can simulate the failure by temporarily making GPU1 busy (if safe) or by using a mock server, but primarily rely on code review and unit tests.
3.  **Verify Cron Syntax:** Ensure the cron entry itself hasn't been broken (though the task is to fix the *model fallback*, not the cron syntax, it's good to confirm the script path is still valid).

#### Phase 4: Reporting to Alex
I will report:
1.  **Root Cause:** The script didn't handle the case where GPU1 was occupied by ComfyUI, leading to a hard failure instead of a graceful fallback.
2.  **Changes Made:** List the specific files modified and a brief summary of the logic added (e.g., "Added try/except in `router_client.py` to catch 500 errors and retry with `qwen3.8-27b-abliterated-gpu0`).
3.  **Verification Results:**
    *   Output of unit tests/linting.
    *   Evidence that the fallback logic is present (snippet from the code).
    *   Confirmation that the cron script is still executable and points to the correct file.
4.  **Next Steps:** Suggest monitoring the next two 4-hourly cron runs to confirm stability.

### 3. Preventing the "Lost Output" Trap
The previous session failed because Claude ran in `/tmp` while verification looked in `~/coding-projects/model-hub`.

**How I prevent this:**
1.  **Explicit `cd`:** My `claude -p` command starts with `cd /home/alex/coding-projects/model-hub &&`. This ensures the shell's working directory is correct *before* Claude starts.
2.  **Absolute Paths in Prompt:** In the prompt to Claude, I explicitly state: *"You are working in the model-hub repository at `/home/alex/coding-projects/model-hub`."* and list files using absolute or relative-to-that-root paths.
3.  **No `--cwd` Ambiguity:** By chaining `cd` with `&&`, the working directory for Claude is guaranteed to be the repo root.
4.  **Post-Hoc Verification Location:** All my `read_file` and test commands will explicitly use the path `/home/alex/coding-projects/model-hub/...`. I will never assume the current directory is the repo unless I have just `cd`'d into it in the same command chain.
5.  **Git Check:** Before starting, I will run `git status` in the repo to ensure it's clean (or note existing changes). After Claude runs, I will run `git diff` in the same directory to see exactly what changed. This confirms the files were modified *in place* in the repo, not in a temp copy.

### Summary of Commands (Mental Draft)
1.  `cd /home/alex/coding-projects/model-hub && git status`
2.  `cat /etc/cron.d/homesrv` (or similar) to find script name.
3.  `read_file <script_name>` and related modules.
4.  `cd /home/alex/coding-projects/model-hub && claude -p "<detailed prompt>"`
5.  `cd /home/alex/coding-projects/model-hub && git diff`
6.  `read_file <changed_files>` to inspect logic.
7.  `cd /home/alex/coding-projects/model-hub && pytest -v` (or similar)
8.  Report to Alex.