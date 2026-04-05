# AgentDebuggerEnv — Implementation Plan

An OpenEnv-compliant debugging environment where AI agents fix broken code through iterative hypothesis-test-fix cycles. Submission for the **Meta + PyTorch + HuggingFace OpenEnv Hackathon**.

## User Review Required

> [!IMPORTANT]
> This is a large project with **15+ files** to create. The entire codebase needs to be built from scratch (only the README exists currently). Please confirm you'd like me to proceed with the full implementation.

> [!WARNING]
> The README specifies `huggingface_space: shashaank/agentdebugger-env`. You'll need to create this HuggingFace Space and deploy the Docker container there for the hackathon submission. I'll build everything locally; deployment is a manual step.

## Proposed Changes

The implementation follows the exact order from the README's Section 14 checklist. Each step depends on the previous.

---

### Step 1: Sandbox (`env/sandbox.py`) — Build & Test First

This is the most security-critical component. Every code execution goes through here.

#### [NEW] [sandbox.py](file:///Users/shashaankjain/Desktop/meta_hackathon/env/sandbox.py)

- `execute_code(code, test_code, allow_threading=False) → (str, bool, int)`
- AST-based import detection (not string matching) to block dangerous imports
- `BLOCKED_IMPORTS` list: os, sys, subprocess, socket, importlib, shutil, pathlib, glob, pickle, shelve, dbm, sqlite3, ftplib, http, urllib, requests, httpx, asyncio, multiprocessing, threading (unless `allow_threading=True`), ctypes, cffi, resource, signal, mmap, gc
- Write code + test_code to a temp file, run in subprocess with `timeout=10`
- Capture merged stdout+stderr
- Clean up temp files in `finally` block

#### [NEW] [test_sandbox.py](file:///Users/shashaankjain/Desktop/meta_hackathon/tests/test_sandbox.py)

- 5 required tests: timeout, os blocked, sys blocked, clean code runs, syntax error returns output

---

### Step 2: Data Models

#### [NEW] [models.py](file:///Users/shashaankjain/Desktop/meta_hackathon/env/models.py)

- `FixAttempt`, `Observation`, `Action`, `Reward` — all Pydantic v2 BaseModel subclasses
- Exact field names and types from README Section 3

---

### Step 3: Task Definitions

#### [NEW] [task_easy.py](file:///Users/shashaankjain/Desktop/meta_hackathon/env/tasks/task_easy.py)

- Binary search with `<` instead of `<=` bug
- 8-test suite, 7 pass initially, 1 fails (last element)
- Ground truth: `hypothesis_keywords`: ["left <= right", "termination", "last element", "off by one", "<="]

#### [NEW] [task_medium.py](file:///Users/shashaankjain/Desktop/meta_hackathon/env/tasks/task_medium.py)

- `hash_password`, `validate_password`, `authenticate_user` — bug is in `hash_password`
- 10-test suite, 6 pass, 4 fail (edge cases with hash mismatch)
- Red herring: error points to `authenticate_user` but bug is in `hash_password`
- Hypothesis must mention "hash_password" AND at least 1 other keyword

#### [NEW] [task_hard.py](file:///Users/shashaankjain/Desktop/meta_hackathon/env/tasks/task_hard.py)

- `ConnectionCounter` with race condition in `increment()`/`decrement()`
- 8 sequential tests all pass on buggy code
- Bug only surfaces under concurrent access
- `allow_threading=True` for this task

#### [NEW] [registry.py](file:///Users/shashaankjain/Desktop/meta_hackathon/env/tasks/registry.py)

- Maps `"easy"` / `"medium"` / `"hard"` → task config dict (buggy_code, test_suite, description, ground_truth, max_attempts, max_steps)

#### [NEW] [`__init__.py` files](file:///Users/shashaankjain/Desktop/meta_hackathon/env/__init__.py)

- `env/__init__.py` and `env/tasks/__init__.py`

---

### Step 4: Graders

#### [NEW] [base_grader.py](file:///Users/shashaankjain/Desktop/meta_hackathon/env/graders/base_grader.py)

- Abstract base class with `score()` method

#### [NEW] [grader_easy.py](file:///Users/shashaankjain/Desktop/meta_hackathon/env/graders/grader_easy.py)

- Standard formula: 0.60 test_pass_ratio + 0.20 efficiency + 0.15 hypothesis + 0.05 early_solve

#### [NEW] [grader_medium.py](file:///Users/shashaankjain/Desktop/meta_hackathon/env/graders/grader_medium.py)

- Same formula but with red herring detection: hypothesis mentioning only "authenticate_user" scores 0.0

#### [NEW] [grader_hard.py](file:///Users/shashaankjain/Desktop/meta_hackathon/env/graders/grader_hard.py)

- Custom weights: 0.40 original tests + 0.30 concurrent stress test + 0.20 hypothesis + 0.10 efficiency
- Runs a 1000-thread concurrent stress test against submitted code

#### [NEW] [test_graders.py](file:///Users/shashaankjain/Desktop/meta_hackathon/tests/test_graders.py)

- Determinism tests (same input → same output)
- Range tests (output always in [0.0, 1.0])

---

### Step 5: Environment Core

#### [NEW] [environment.py](file:///Users/shashaankjain/Desktop/meta_hackathon/env/environment.py)

- `DebuggerEnvironment` class with `reset(task_id)`, `step(action)`, `state()` methods
- `reset()`: loads task, runs buggy code through sandbox to get initial error output
- `step()`: routes by `action_type` — submit_fix → sandbox, query_context → return info, give_up → run grader
- All action rules from Section 3.2 implemented exactly
- Step-level reward calculation per Section 6.1
- Episode-level grader invocation on `done=True`
- Never crashes — all errors returned in `info["error"]`

#### [NEW] [test_environment.py](file:///Users/shashaankjain/Desktop/meta_hackathon/tests/test_environment.py)

- Unit tests for reset/step/state

---

### Step 6: FastAPI Server

#### [NEW] [server.py](file:///Users/shashaankjain/Desktop/meta_hackathon/env/server.py)

- `POST /reset` — body: `{"task_id": "easy"}`, returns Observation JSON
- `POST /step` — body: Action JSON, returns `{"observation", "reward", "done", "info"}`
- `GET /state` — returns full state dict
- `GET /health` — returns `{"status": "ok", "environment": "agentdebugger-env", "version": "1.0.0"}` with HTTP 200

---

### Step 7: Inference Script

#### [NEW] [inference.py](file:///Users/shashaankjain/Desktop/meta_hackathon/inference.py)

- Exact code from README Section 8 — already fully specified
- Root directory placement (not in `env/`)
- Reads env vars: `API_BASE_URL`, `MODEL_NAME`, `HF_TOKEN`, `ENV_BASE_URL`
- Uses `openai` Python client
- Saves `baseline_results.json`

---

### Step 8: Configuration & Deployment

#### [NEW] [openenv.yaml](file:///Users/shashaankjain/Desktop/meta_hackathon/openenv.yaml)

- Exact content from README Section 9

#### [NEW] [Dockerfile](file:///Users/shashaankjain/Desktop/meta_hackathon/Dockerfile)

- Exact content from README Section 10

#### [NEW] [requirements.txt](file:///Users/shashaankjain/Desktop/meta_hackathon/requirements.txt)

- Exact content from README Section 11

---

## Open Questions

> [!IMPORTANT]
> **Task Medium — The Hash Bug:** The README describes a bytes/str conversion bug in `hash_password` where `str()` wrapping adds `"b'"` prefix. I need to carefully design the `user_db` and test setup so that 6 tests pass and exactly 4 fail. The README leaves the exact test suite design for medium to the implementer. I'll design it to match the described behavior. Any preferences?

> [!IMPORTANT]
> **Hard Task Test Count:** The README says `tests_total: 8` for hard in `openenv.yaml`, but the hard task has 8 sequential tests (all pass) and the agent needs to design a concurrent test. The grader independently runs its own 1000-thread stress test. I'll keep `tests_total: 8` as the initial suite and the grader adds its own concurrent verification separately. Correct?

## Verification Plan

### Automated Tests
1. `pytest tests/test_sandbox.py -v` — All 5 sandbox tests pass
2. `pytest tests/test_graders.py -v` — Determinism and range tests pass
3. `pytest tests/test_environment.py -v` — Reset/step/state tests pass
4. Start server with `uvicorn env.server:app --port 8000`, then:
   - `curl http://localhost:8000/health` → 200 with correct JSON
   - POST `/reset` for each task → valid Observation
   - POST `/step` with various actions → correct responses
5. Variance self-check:
   - Dummy agent (submits `pass`) → scores < 0.15
   - Perfect agent (ground truth fix + correct hypothesis) → scores > 0.85 on easy

### Manual Verification
- Docker build: `docker build -t agentdebugger-env .`
- Docker run and health check
- User deploys to HuggingFace Space and runs `openenv validate .`
