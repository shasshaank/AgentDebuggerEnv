---
title: AgentDebugger Env
emoji: 📈
colorFrom: yellow
colorTo: green
sdk: docker
app_port: 8000
pinned: false
---

# AgentDebuggerEnv 🐛

> An OpenEnv-compliant environment where AI agents debug broken code through iterative hypothesis-test-fix cycles — benchmarking genuine agentic reasoning, not static code reading.

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## SECTION 0: CONTEXT FOR THE IMPLEMENTING AI
## Read this completely before writing a single line of code.
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This project is a submission for the **Meta + PyTorch + HuggingFace OpenEnv Hackathon**. Every implementation decision must be made with the hackathon's judging pipeline in mind. This section explains the full context — what the hackathon is, how judging works, what gets you disqualified, and what wins. Do not skip this.

---

### 0.1 What is OpenEnv?

OpenEnv is a standardized interface for building environments where AI agents learn from interaction — the same paradigm as OpenAI Gym, but for real-world tasks instead of games. Every OpenEnv environment must implement exactly three core methods:

- `reset(task_id)` → Returns the initial Observation. The agent's clean starting state.
- `step(action)` → Agent submits one action → Environment returns (new Observation, Reward, done: bool, info: dict)
- `state()` → Returns the full internal environment state as a plain dict

These three methods must be exposed as HTTP REST endpoints via a FastAPI server, containerized with Docker, and deployed to a HuggingFace Space. The hackathon's own CLI tool (`openenv validate`) runs automated checks against these endpoints.

---

### 0.2 Why This Hackathon Matters — The Stakes

This hackathon is organized by **Meta AI** and sponsored by **PyTorch** and **HuggingFace** — three of the most influential organizations in open-source AI research. The judges are not students or generalist engineers. They are:

- Meta AI researchers who actively publish on LLM agents, tool use, and reasoning
- HuggingFace engineers who maintain the open-source model ecosystem
- PyTorch team members who work on the training infrastructure frontier models run on

A strong submission here has direct, real consequences:

1. **Visibility**: Winning or placing gets your environment featured on HuggingFace Hub, adopted by researchers, and cited in future benchmark papers. This is the kind of credibility that opens research internship doors at Meta, Google DeepMind, and similar labs.
2. **Research impact**: A well-designed environment with clean graders gets used by the community for years. SWE-bench, which inspired this environment, now appears in nearly every LLM agent paper.
3. **Career signal**: A national-level hackathon win sponsored by Meta is a tier-1 resume signal for a third-year CS student, especially when the project directly connects to ML agent research.

The judges will read your environment design the way a reviewer reads a research paper. They will check: Is this domain real? Is the grader honest? Does the hard task actually challenge frontier models? A shallow or broken submission will be obvious to them immediately.

---

### 0.3 How Judging Works — Every Phase Explained

**Phase 1: Automated Validation (Pass/Fail Gate)**

This phase is entirely automated. You either pass all checks or you are disqualified. No partial credit. The checks are:

- HF Space must be live and return HTTP 200 on a ping to `/health`
- `POST /reset` must return a valid Observation JSON
- `openenv.yaml` must parse correctly and match the spec schema
- `docker build` must complete without errors
- `inference.py` must run end-to-end without crashing and produce a `baseline_results.json` file
- All 3 tasks must be enumerable and each grader must return a float in [0.0, 1.0]

**Phase 2: Agentic Evaluation (Scored)**

The hackathon runs their own standard agent (Nemotron 3 Super) against your environment. They measure:

- **Score variance**: Do different agents get meaningfully different scores? If a random agent and GPT-4o get the same score, your graders are broken and this phase fails.
- **Score reproducibility**: Does re-running `inference.py` produce the same scores? Graders must be deterministic.
- **Baseline verification**: They re-run your `inference.py` and check that scores match what you reported.

**Phase 3: Human Review (Top Submissions Only)**

Meta and HuggingFace engineers manually review top submissions and score on:
- Real-world utility: Would a real engineering team or research group actually use this?
- Creativity and novelty: Does this environment exist anywhere else?
- Exploit resistance: Can an agent game the grader without actually doing the task?
- Code quality: Is the implementation clean and the environment well-designed?

---

### 0.4 Disqualification Criteria — Avoid All of These

| Violation | Why it disqualifies |
|---|---|
| Environment does not deploy or `/health` returns non-200 | Automated ping fails Phase 1 immediately |
| `inference.py` not in root directory | Hard requirement — automated script looks for it there |
| `inference.py` crashes or errors | Phase 1 baseline check fails |
| Graders always return the same score | Phase 2 variance check fails |
| `docker build` fails | Phase 1 Dockerfile check fails |
| Plagiarized or trivially copied existing environment | Phase 3 human review disqualifies |
| Agent can game the grader without doing the task | Phase 3 exploit check disqualifies |

---

### 0.5 Hard Infrastructure Constraints — Non-Negotiable

Every constraint below is a hard requirement. Violating any of them causes disqualification or incorrect behavior during automated evaluation:

```
inference.py          Must be named EXACTLY this. Must be in the ROOT directory. Not in /env/, not in /src/. ROOT.
API_BASE_URL          Must be read from os.environ. Never hardcoded.
MODEL_NAME            Must be read from os.environ. Never hardcoded.
HF_TOKEN              Must be read from os.environ. Never hardcoded.
OpenAI client         All LLM calls must use the openai Python library. Not anthropic. Not direct HTTP requests.
20-minute limit       inference.py must complete ALL 3 tasks in under 20 minutes total.
2 vCPU / 8GB RAM      Environment server must run within these limits. NO ML models loaded server-side.
Port 8000             Server must listen on port 8000.
/health endpoint      Must exist and return HTTP 200. This is the automated deployment ping.
```

---

### 0.6 The Biggest Technical Risk: Code Execution Sandbox

This environment executes agent-generated Python code. This is the most dangerous part of the implementation. The hackathon's automated evaluation will run an LLM agent against your environment — that agent may generate code like `import os; os.system("rm -rf /")` or an infinite loop. If your sandbox does not handle this, the HF Space crashes and you fail Phase 1.

**The sandbox must implement ALL of the following:**

1. **Hard execution timeout**: Every code execution attempt must be killed after a maximum of 10 seconds. Use `subprocess` with `timeout=10`, or `signal.alarm(10)` with a SIGALRM handler.
2. **Restricted imports**: Remove dangerous builtins before exec. At minimum, block: `os`, `sys`, `subprocess`, `importlib`, `__import__`, `open`, `eval`, `exec`, `compile`.
3. **Memory limit**: Use `resource.setrlimit(resource.RLIMIT_AS, ...)` to cap memory usage per execution at 256MB.
4. **No network access**: The executed code must not be able to make network calls. Achieved by the restricted imports above.
5. **Clean state per attempt**: Each execution must run in a completely fresh namespace. No state leaks between attempts.

**Implement the sandbox as a separate module** `env/sandbox.py`. Every code execution in the environment must go through this module. Never call `exec()` directly in environment code.

---

### 0.7 The Second Biggest Risk: SWE-bench Differentiation

The judges will immediately ask: "How is this different from SWE-bench?" If you cannot answer this through the implementation itself (not just the README), Phase 3 scores suffer.

**The answer is the iterative feedback loop.** SWE-bench gives an agent a static codebase and measures only the final patch. AgentDebuggerEnv gives the agent a live execution environment and measures the entire debugging trajectory — every hypothesis, every fix attempt, every error observation, every iteration. The reward function provides signal at every step, not just at episode end.

**Make this difference viscerally obvious in the implementation:**
- The Observation must include `previous_attempts` — a list of every (code_submitted, error_output, hypothesis) triple from this episode
- The Reward must be non-zero at intermediate steps, not just when tests pass
- The `info` dict must include `hypothesis_accuracy` — did the agent's stated hypothesis match the actual bug?
- The hard task must require multiple iterations — a single-shot fix attempt must fail

---

### 0.8 Scoring Rubric — What the Judges Are Weighing

| Category | Weight | What wins points |
|---|---|---|
| Real-world utility | 30% | Would Meta's engineering team actually benchmark on this? |
| Task & grader quality | 25% | Are graders deterministic? Does hard task challenge GPT-4o? |
| Environment design | 20% | Dense reward? Clean reset? Well-typed observations? |
| Code quality & spec compliance | 15% | Does openenv validate pass? Does Docker build? |
| Creativity & novelty | 10% | Domain we haven't seen in OpenEnv? Clever mechanics? |

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## SECTION 1: PROJECT OVERVIEW
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Debugging is one of the highest-leverage cognitive tasks in software engineering. Studies consistently show that developers spend 35–50% of their time debugging — more than writing new code. Unlike code review (which is static reading), debugging requires a genuine hypothesis-test-fix feedback loop: form a theory about what's wrong, attempt a fix, observe what breaks next, update the theory, repeat.

Current LLM agents fail at debugging in measurable, specific ways:
- They generate plausible-looking fixes that don't address the root cause
- They ignore new error information and repeat the same fix attempt
- They follow misleading error messages to the wrong function (red herring failures)
- They cannot detect bugs that only manifest under specific execution conditions

**AgentDebuggerEnv** makes all four of these failures measurable and scorable through a live, iterative execution environment. The agent submits code fixes, the environment executes them in a sandbox, returns the actual test output, and the agent must update its hypothesis and try again — exactly like a real developer at a terminal.

This is not a static QA benchmark. It is a genuine agentic loop.

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## SECTION 2: PROJECT STRUCTURE
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
agentdebugger-env/
├── inference.py                        # ← MUST BE HERE IN ROOT. Hackathon hard requirement.
├── env/
│   ├── __init__.py
│   ├── environment.py                  # Core OpenEnv class: reset(), step(), state()
│   ├── models.py                       # All Pydantic models: Observation, Action, Reward
│   ├── sandbox.py                      # Code execution sandbox — ALL exec goes through here
│   ├── server.py                       # FastAPI server exposing /reset, /step, /state, /health
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── registry.py                 # Maps task_id → task config + buggy code + test suite
│   │   ├── task_easy.py                # Task 1: Single function, one clear bug
│   │   ├── task_medium.py              # Task 2: Three interdependent functions, red herring error
│   │   └── task_hard.py               # Task 3: Concurrency race condition
│   └── graders/
│       ├── __init__.py
│       ├── base_grader.py              # Abstract base: score(submitted_attempts) → float
│       ├── grader_easy.py
│       ├── grader_medium.py
│       └── grader_hard.py
├── tests/
│   ├── test_environment.py             # Unit tests for reset/step/state
│   ├── test_sandbox.py                 # Tests that sandbox correctly blocks dangerous code
│   └── test_graders.py                # Tests graders return [0.0, 1.0] and are deterministic
├── openenv.yaml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## SECTION 3: DATA MODELS (Implement Exactly as Specified)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

All models must be Pydantic v2 BaseModel subclasses. All fields must have types. No Optional fields without defaults. These exact field names and types are required for `openenv validate` to pass.

### 3.1 Observation

```python
from pydantic import BaseModel
from typing import List, Dict, Optional

class FixAttempt(BaseModel):
    attempt_number: int           # 1-indexed attempt number this episode
    code_submitted: str           # The full code the agent submitted for this attempt
    hypothesis: str               # Agent's stated hypothesis about the bug before this attempt
    execution_output: str         # Full stdout + stderr from running the test suite
    tests_passed: int             # Number of tests that passed after this fix
    tests_total: int              # Total number of tests in the suite
    execution_time_ms: int        # How long the sandbox took to run (milliseconds)
    timed_out: bool               # Whether this attempt hit the 10-second sandbox timeout

class Observation(BaseModel):
    # Task context — fixed for the episode
    task_id: str                  # "easy" | "medium" | "hard"
    task_description: str         # Plain English description of what the code is supposed to do
    buggy_code: str               # The original broken code (shown once at reset, always available)
    test_suite: str               # The full test suite code (agent can read this to understand requirements)
    initial_error_output: str     # Output of running the test suite against the buggy code at reset()

    # Dynamic state — changes each step
    current_code: str             # The most recent version of the code (after agent's last fix attempt)
    current_error_output: str     # Output of running tests against current_code
    tests_passed: int             # Tests passing on current_code
    tests_total: int              # Total tests in suite
    previous_attempts: List[FixAttempt]  # Full history of all fix attempts this episode

    # Budget tracking
    attempts_remaining: int       # How many more fix submissions are allowed
    max_attempts: int             # Total attempt budget for this task

    # Step tracking
    step_number: int              # Current step number (increments on every action)
    max_steps: int                # Total step budget (includes both fix and query actions)
    done: bool                    # Whether the episode has ended

    # Scoring signal (shown to agent for learning)
    score_estimate: float         # Running estimate of current grader score (0.0–1.0)
    hint_used: bool               # Whether the agent has used their one hint this episode
```

### 3.2 Action

The agent submits exactly one Action per step. There are three action types. These are mutually exclusive.

```python
class Action(BaseModel):
    action_type: str              # "submit_fix" | "query_context" | "give_up"

    # ── submit_fix ────────────────────────────────────────────────────────────
    # Used when action_type == "submit_fix"
    # This is the primary action. The agent submits a complete, corrected version
    # of the code. The environment runs it against the test suite and returns results.
    fixed_code: Optional[str] = None       # Complete corrected code (not a diff — full file)
    hypothesis: Optional[str] = None       # Agent's stated hypothesis about the bug.
                                           # REQUIRED even with submit_fix. Used for scoring.

    # ── query_context ─────────────────────────────────────────────────────────
    # Used when action_type == "query_context"
    # Agent requests additional context without spending a fix attempt.
    # Each episode has ONE free query. Additional queries cost -0.05 reward each.
    # Does NOT count against attempts_remaining. DOES count against max_steps.
    query_type: Optional[str] = None       # "function_signature" | "related_code" |
                                           #  "error_explanation" | "test_details"
    query_target: Optional[str] = None     # What to query. E.g. function name, line number.

    # ── give_up ───────────────────────────────────────────────────────────────
    # Used when action_type == "give_up"
    # Agent explicitly surrenders. Ends the episode. Better than truncation.
    # Triggers grader with current best attempt scores.
    final_diagnosis: Optional[str] = None  # Agent's final explanation of what the bug was
```

#### Action Rules (implement exactly these — they affect grader scores):

| Rule | Implementation detail |
|---|---|
| `submit_fix` without `hypothesis` | Return step_reward = -0.1, error in info["error"], do NOT execute the code, do NOT count the attempt |
| `submit_fix` with syntactically invalid Python | Execute it anyway (sandbox will catch the SyntaxError), count the attempt, return the SyntaxError as execution_output |
| `query_context` first use | Free. Return requested context in info["query_result"]. No reward change. |
| `query_context` subsequent uses | Return context but apply -0.05 to step_reward. Still free of attempts_remaining. |
| `query_context` with invalid query_type | Return step_reward = -0.05, error in info, do not spend the free query |
| `give_up` | Set done=True immediately. Run grader on best attempt. Return grader_score in final Reward. |
| Exceeding max_steps | Force done=True. Apply -0.20 truncation penalty. Run grader on best attempt. |
| Exceeding attempts_remaining | Refuse the fix: return step_reward = -0.15, error in info["error"]. Agent can still query_context or give_up. |

### 3.3 Reward

```python
class Reward(BaseModel):
    step_reward: float            # Reward for THIS step only. Range: -1.0 to +1.0
    cumulative_reward: float      # Sum of all step_rewards this episode
    grader_score: float           # 0.0 during episode. Set ONLY on terminal step (done=True).
                                  # This is the official score used for ranking. Range: 0.0–1.0
    breakdown: Dict[str, float]   # Itemized components. Always populate this — used for debugging
                                  # and for the Phase 2 variance analysis. Example:
                                  # {"test_progress": 0.2, "hypothesis_match": 0.1,
                                  #  "efficiency_bonus": 0.05, "false_fix_penalty": 0.0}
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## SECTION 4: ENVIRONMENT API (FastAPI Endpoints)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### POST /reset

Starts a completely fresh episode. Clears all state from any previous episode. Returns initial Observation.

```
Request body:  { "task_id": "easy" }   (string, required)
Response:      Observation JSON
HTTP status:   200 on success, 400 on invalid task_id
```

The Observation returned by reset() must include:
- `buggy_code`: the full broken source file
- `test_suite`: the full test file
- `initial_error_output`: the output of running the test suite against buggy_code RIGHT NOW at reset time (run it in the sandbox on reset, cache the result)
- `current_code` == `buggy_code` (no fixes applied yet)
- `previous_attempts` == [] (empty list)
- `attempts_remaining` == task's max_attempts config value
- `tests_passed` == however many tests pass on the buggy code (may be > 0 for medium/hard tasks)
- `done` == False

### POST /step

Submit one action. Advance the environment by one step.

```
Request body:  Action JSON
Response:      { "observation": Observation, "reward": Reward, "done": bool, "info": dict }
HTTP status:   200 always (never 500 — handle all errors gracefully and return them in info["error"])
```

The `info` dict must always contain:
```python
{
    "step_number": int,
    "attempts_used": int,
    "attempts_remaining": int,
    "tests_passed": int,
    "tests_total": int,
    "hypothesis_matched_bug": bool | None,  # None until episode ends or grader has signal
    "query_result": str | None,             # Populated when action_type == "query_context"
    "error": str | None,                    # Human-readable error message if action was invalid
    "execution_time_ms": int | None,        # Sandbox execution time for this attempt
    "timed_out": bool                       # Whether sandbox timed out this attempt
}
```

### GET /state

Returns the full internal environment state. Required by OpenEnv spec.

```
Response: {
    "task_id": str,
    "step_number": int,
    "attempts_used": int,
    "current_tests_passed": int,
    "current_tests_total": int,
    "best_tests_passed": int,         # Best test pass count achieved in any attempt this episode
    "all_hypotheses": List[str],      # All hypotheses submitted so far
    "cumulative_reward": float,
    "done": bool,
    "hint_used": bool
}
```

### GET /health

**This endpoint is critical. The hackathon's automated deployment check pings this URL. If it returns anything other than HTTP 200, Phase 1 fails immediately.**

```
Response:      { "status": "ok", "environment": "agentdebugger-env", "version": "1.0.0" }
HTTP status:   200 always
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## SECTION 5: SANDBOX (Critical — Implement First)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The sandbox is the most security-critical component. Every `submit_fix` action goes through this. Implement it as `env/sandbox.py` before implementing anything else. It must be correct before the environment goes live.

```python
# env/sandbox.py
# ALL code execution in the environment must go through execute_code().
# Never call exec() or subprocess directly anywhere else.

import subprocess
import tempfile
import os
import sys
from typing import Tuple

BLOCKED_IMPORTS = [
    "os", "sys", "subprocess", "socket", "importlib", "shutil",
    "pathlib", "glob", "pickle", "shelve", "dbm", "sqlite3",
    "ftplib", "http", "urllib", "requests", "httpx", "asyncio",
    "multiprocessing", "threading",  # threading allowed only in task_hard — see below
    "ctypes", "cffi", "resource", "signal", "mmap", "gc"
]

EXECUTION_TIMEOUT_SECONDS = 10
MEMORY_LIMIT_MB = 256

def execute_code(code: str, test_code: str, allow_threading: bool = False) -> Tuple[str, bool, int]:
    """
    Execute code + test_code in a sandboxed subprocess.
    
    Returns:
        (output: str, timed_out: bool, execution_time_ms: int)
    
    The output contains both stdout and stderr merged, exactly as a developer
    would see in their terminal. This is what gets returned in the Observation.
    
    Implementation requirements:
    1. Write code + test_code to a temporary file
    2. Run it in a subprocess with timeout=EXECUTION_TIMEOUT_SECONDS
    3. Capture stdout + stderr merged (subprocess.PIPE with stderr=subprocess.STDOUT)
    4. Kill the subprocess if it exceeds timeout
    5. Return the output, whether it timed out, and elapsed time in ms
    6. Clean up temp files in a finally block — always
    
    The allow_threading flag is True ONLY for task_hard, which intentionally
    uses threading to create the race condition. For easy and medium tasks,
    threading is in BLOCKED_IMPORTS.
    
    Blocking mechanism: Prepend a validation script to the temp file that
    checks for blocked imports using AST parsing before exec. If a blocked
    import is detected, print an error and exit(1) before running any code.
    Use ast.parse() + ast.walk() to find ast.Import and ast.ImportFrom nodes.
    """
    pass  # Implement this
```

**Sandbox test cases you must write in `tests/test_sandbox.py`:**

```python
def test_timeout_enforcement():
    # Code with infinite loop must return timed_out=True within 11 seconds
    code = "while True: pass"
    output, timed_out, _ = execute_code(code, "")
    assert timed_out == True

def test_os_import_blocked():
    code = "import os; os.system('echo pwned')"
    output, timed_out, _ = execute_code(code, "")
    assert "pwned" not in output

def test_sys_import_blocked():
    code = "import sys; sys.exit(0)"
    output, _, _ = execute_code(code, "")
    assert "blocked" in output.lower() or "import" in output.lower()

def test_clean_code_runs():
    code = "def add(a, b): return a + b"
    test = "assert add(2, 3) == 5\nprint('PASSED')"
    output, timed_out, _ = execute_code(code, test)
    assert "PASSED" in output
    assert timed_out == False

def test_syntax_error_returns_output():
    code = "def broken(: pass"
    output, timed_out, _ = execute_code(code, "")
    assert "SyntaxError" in output
    assert timed_out == False
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## SECTION 6: REWARD FUNCTION
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The reward function must provide dense signal throughout the episode. An RL agent must be able to learn from intermediate steps, not just the final outcome. Every step must return a non-trivial step_reward.

### 6.1 Step-Level Rewards

| Event | Reward | Notes |
|---|---|---|
| Fix attempt increases tests passing (e.g. 3→5 of 8) | +0.15 × (new_passed - prev_passed) / total | Scaled progress reward |
| Fix attempt decreases tests passing | -0.10 × (prev_passed - new_passed) / total | Regression penalty |
| Fix attempt makes no change to passing count | -0.05 | Stagnation penalty |
| All tests pass (episode solved) | +0.50 | Major bonus on top of progress reward |
| Hypothesis matches actual bug (verified at end) | +0.10 | Rewards correct reasoning, not just lucky fixes |
| Hypothesis is completely wrong direction | -0.05 | Penalizes random guessing |
| Fix attempt times out in sandbox | -0.10 | Penalizes infinite loops in submitted code |
| Submit fix without hypothesis field | -0.10 | Hypothesis is required — see Action rules |
| First `query_context` use | 0.00 | Free |
| Subsequent `query_context` uses | -0.05 each | Diminishing returns on hints |
| `give_up` action | 0.00 step reward | Grader runs on best attempt |
| Episode truncated (max_steps exceeded) | -0.20 | Penalizes indecision |

### 6.2 Episode-Level Grader Score

The grader runs ONLY when done=True (either tests all pass, agent gives up, or max_steps exceeded). It produces the official `grader_score` float in [0.0, 1.0].

```
grader_score = test_pass_ratio           (weight: 0.60)
             + efficiency_bonus          (weight: 0.20)
             + hypothesis_accuracy       (weight: 0.15)
             + early_solve_bonus         (weight: 0.05)

where:

test_pass_ratio    = best_tests_passed / tests_total
                     (best across ALL attempts this episode, not just final)

efficiency_bonus   = max(0, (max_attempts - attempts_used) / max_attempts) × 0.20
                     (reward for solving with fewer attempts)

hypothesis_accuracy = fraction of submitted hypotheses that correctly identified
                      the bug location (correct function name mentioned) × 0.15

early_solve_bonus  = 0.05 if all tests pass AND attempts_used <= ceil(max_attempts / 3)
                     else 0.0
```

**Grader score variance guarantee:** A random agent (submits random code each attempt) will score 0.0–0.15 on all tasks. A perfect agent (correct fix on first attempt with correct hypothesis) will score 0.95–1.0. This guarantees the Phase 2 variance check passes.

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## SECTION 7: TASKS
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each task is defined by: buggy_code, test_suite, ground_truth_bug_description, ground_truth_fix, and the keyword(s) that must appear in a correct hypothesis. These are stored as Python dictionaries in each task file and loaded by registry.py.

---

### Task 1 — Easy: Single Function, One Clear Bug

**Difficulty:** Easy | **Max attempts:** 5 | **Max steps:** 8
**Expected GPT-4o score:** ~0.85

**Scenario:** A utility module for a data processing pipeline. One function has a bug that produces a clear, informative error message pointing directly at the problem. One to two fix iterations should be enough.

**The bug:** An off-by-one error in a binary search implementation. The function searches for a target value in a sorted list. The termination condition uses `<` instead of `<=`, causing the function to miss the target when it's the last element of the list. The error is a failing assertion with a clear message: `AssertionError: binary_search([1,2,3,4,5], 5) returned -1, expected 4`.

**Buggy code to implement in task_easy.py:**
```python
def binary_search(arr: list, target: int) -> int:
    """Return the index of target in sorted arr, or -1 if not found."""
    left, right = 0, len(arr) - 1
    while left < right:          # BUG: should be left <= right
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
```

**Test suite (8 tests) — the grader is these tests passing:**
```python
import pytest
from solution import binary_search

def test_finds_first_element():
    assert binary_search([1, 3, 5, 7, 9], 1) == 0

def test_finds_middle_element():
    assert binary_search([1, 3, 5, 7, 9], 5) == 2

def test_finds_last_element():
    assert binary_search([1, 3, 5, 7, 9], 9) == 4  # THIS IS THE FAILING TEST

def test_returns_minus_one_for_missing():
    assert binary_search([1, 3, 5, 7, 9], 4) == -1

def test_single_element_found():
    assert binary_search([42], 42) == 0

def test_single_element_not_found():
    assert binary_search([42], 7) == -1

def test_empty_list():
    assert binary_search([], 5) == -1

def test_finds_second_to_last():
    assert binary_search([2, 4, 6, 8, 10], 8) == 3
```

**Initial error output (shown in reset() Observation):**
```
FAILED test_suite.py::test_finds_last_element - AssertionError: assert -1 == 4
7 passed, 1 failed
```

**Ground truth for grader:**
- `ground_truth_bug_location`: "binary_search" (function name)
- `ground_truth_bug_type`: "off_by_one"
- `hypothesis_keywords`: ["left <= right", "termination", "last element", "off by one", "<="]
- A hypothesis matches if it contains at least 1 of these keywords (case-insensitive)

**Why it's easy:** Error message directly names the failing test and the expected vs actual value. One read of the while condition reveals the bug. The fix is a single character change.

---

### Task 2 — Medium: Three Interdependent Functions, Red Herring Error

**Difficulty:** Medium | **Max attempts:** 7 | **Max steps:** 15
**Expected GPT-4o score:** ~0.50

**Scenario:** A simple user authentication module with three interdependent functions: `hash_password`, `validate_password`, and `authenticate_user`. The error message points to `authenticate_user` but the actual bug is in `hash_password`. The agent must trace backwards from symptom to cause.

**The bug:** `hash_password` uses `hashlib.md5` and calls `.hexdigest()` but then wraps the result in `str()` unnecessarily, which adds the string `"b'"` prefix and `"'"` suffix to the hash in Python 3 (this happens because an intermediate step converts to bytes then back incorrectly). The `validate_password` function hashes the input and compares — but the stored hash was created with the buggy function, so when authenticate is called with correct credentials, comparison always fails and returns False.

**Why the red herring works:** The failing test error says `authenticate_user('alice', 'correct_password') returned False` — which looks like a bug in `authenticate_user`. The agent's first instinct will be to look at the authentication logic. But `authenticate_user` is completely correct — it calls `validate_password` correctly. `validate_password` is also correct in structure — it compares properly. The bug is in `hash_password`, which is called by both the setup (storing the hash) and validation (checking the input hash). Because both sides are broken the same way, the stored hash and the computed hash are both wrong in the same way — EXCEPT when the password is first stored via a different code path that doesn't use the buggy hash function.

**Implement the full buggy module in task_medium.py with:**
- `hash_password(password: str) -> str` — contains the subtle bytes/str conversion bug
- `validate_password(password: str, stored_hash: str) -> bool` — correct implementation
- `authenticate_user(username: str, password: str, user_db: dict) -> bool` — correct implementation
- 10-test suite where 6 tests pass (basic happy path) and 4 fail (edge cases involving the hash mismatch)

**Ground truth for grader:**
- `ground_truth_bug_location`: "hash_password"
- `hypothesis_keywords`: ["hash_password", "bytes", "str(", "hexdigest", "encoding", "b'"]
- A hypothesis matches if it mentions "hash_password" AND at least 1 other keyword
- A hypothesis that only mentions "authenticate_user" scores 0.0 for hypothesis_accuracy (red herring was followed)

**Why it's medium:** The error message is genuinely misleading. The agent must look at more than one function, understand data flow between them, and resist the red herring. GPT-4o follows red herrings in error messages approximately 50% of the time in this class of problem.

---

### Task 3 — Hard: Concurrency Race Condition

**Difficulty:** Hard | **Max attempts:** 10 | **Max steps:** 25
**Expected GPT-4o score:** ~0.18

**Scenario:** A thread-safe counter implementation used in a web server to track active connections. It uses threading but has a classic race condition: the read-modify-write cycle on the counter is not atomic. Under sequential access, it works perfectly — all 8 existing tests pass. The bug only manifests under concurrent access with specific thread interleaving.

**The bug:** `increment()` and `decrement()` methods read `self.count`, compute `self.count ± 1`, then write back — as three separate operations without holding a lock. The lock is acquired per-operation but not across the read-modify-write sequence.

```python
import threading

class ConnectionCounter:
    """Thread-safe connection counter for a web server."""
    
    def __init__(self):
        self.count = 0
        self._lock = threading.Lock()
    
    def increment(self):
        with self._lock:
            current = self.count      # read
        # ← LOCK RELEASED HERE — race window
        new_val = current + 1         # modify  
        with self._lock:
            self.count = new_val      # write
    
    def decrement(self):
        with self._lock:
            current = self.count
        new_val = current - 1
        with self._lock:
            self.count = new_val
    
    def get_count(self) -> int:
        with self._lock:
            return self.count
```

**The 8 existing tests (all pass on buggy code — sequential access only):**
```python
def test_initial_count_zero(): ...
def test_single_increment(): ...
def test_single_decrement(): ...
def test_multiple_increments(): ...
def test_multiple_decrements(): ...
def test_increment_then_decrement(): ...
def test_get_count_thread_safe(): ...
def test_count_never_negative(): ...
```

**What makes this hard — the agent must:**
1. Recognize that 8/8 sequential tests passing does NOT mean the code is correct
2. Understand that the bug only manifests under concurrent load
3. **Design a new concurrent test** that surfaces the race condition (this is the key step)
4. Fix the implementation (move the entire read-modify-write inside a single `with self._lock:` block)
5. Verify the fix passes ALL 8 original tests + the new concurrent test they designed

**The correct concurrent test an agent must write to surface the bug:**
```python
def test_concurrent_increments():
    counter = ConnectionCounter()
    threads = [threading.Thread(target=counter.increment) for _ in range(100)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert counter.get_count() == 100  # Will fail intermittently on buggy code
```

**IMPORTANT implementation note for task_hard.py:** The sandbox's `allow_threading=True` flag must be set when executing this task's code. This is the ONLY task where threading is permitted in the sandbox.

**Grader special logic for hard task:**
- +0.40 if final code passes all 8 original tests
- +0.30 if final code passes a concurrent stress test (run 1000 concurrent increments, assert count == 1000)
- +0.20 for hypothesis_accuracy (must mention "race condition" OR "atomic" OR "lock" AND "read-modify-write" OR "not atomic" OR "interleaving")
- +0.10 efficiency bonus if solved within 5 attempts

**Why it's hard:** Race conditions are the hardest class of bug to debug. They are non-deterministic (the bug may not appear on every run). The agent must reason about concurrent execution, recognize that passing tests are not sufficient proof of correctness, design a test that makes the non-determinism deterministic, AND then fix the atomicity issue. GPT-4o fails this class of problem approximately 80% of the time.

**Ground truth for grader:**
- `ground_truth_bug_location`: "increment AND decrement"  
- `hypothesis_keywords`: ["race condition", "atomic", "lock", "read-modify-write", "interleaving", "not thread-safe", "release the lock"]

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## SECTION 8: BASELINE INFERENCE SCRIPT
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**File must be named `inference.py`. Must be in the ROOT directory. This is a hard hackathon requirement — the automated validator looks for it at this exact path.**

```python
"""
AgentDebuggerEnv Baseline Inference Script
==========================================
Filename: inference.py (ROOT directory — not in any subdirectory)

Reads from environment variables (never hardcoded):
  API_BASE_URL  — LLM API endpoint
  MODEL_NAME    — Model identifier
  HF_TOKEN      — API key / HuggingFace token

Uses openai Python client for all LLM calls (hackathon requirement).
Must complete all 3 tasks in under 20 minutes total.
Saves results to baseline_results.json on completion.
"""

import os
import json
import time
import re
from openai import OpenAI
import requests

# ── Environment variables (never hardcode these) ──────────────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME", "gpt-4o")
HF_TOKEN     = os.environ.get("HF_TOKEN", "")
ENV_BASE_URL = os.environ.get("ENV_BASE_URL", "http://localhost:8000")

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

SYSTEM_PROMPT = """You are an expert software debugger. You will be given broken code and a
failing test suite. Your job is to:
1. Analyze the error output carefully
2. Form a hypothesis about the root cause (required for every fix attempt)
3. Submit a corrected version of the complete code
4. Observe the new test results and update your hypothesis if needed
5. Repeat until all tests pass or you run out of attempts

You must ALWAYS respond with a valid JSON action object. Available actions:

Submit a fix:
{
  "action_type": "submit_fix",
  "fixed_code": "<complete corrected Python code as a string>",
  "hypothesis": "<your hypothesis about what the bug is and where>"
}

Query for more context (use sparingly — first one is free):
{
  "action_type": "query_context",
  "query_type": "error_explanation" | "function_signature" | "related_code" | "test_details",
  "query_target": "<function name or line number or test name>"
}

Give up (if you cannot find the bug):
{
  "action_type": "give_up",
  "final_diagnosis": "<your best guess at what the bug was>"
}

CRITICAL RULES:
- hypothesis field is REQUIRED in submit_fix — missing it costs reward
- Submit COMPLETE code files, not diffs or partial functions
- Read the error output carefully before each attempt — it tells you what changed
- For concurrent bugs, think about thread safety and atomic operations"""


def parse_action(raw: str) -> dict:
    """Parse LLM response to action dict. Handle markdown code blocks."""
    raw = raw.strip()
    # Strip markdown code blocks if present
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'\s*```$', '', raw, flags=re.MULTILINE)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract first JSON object
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    # Fallback: give up
    return {
        "action_type": "give_up",
        "final_diagnosis": f"Failed to parse response: {raw[:200]}"
    }


def build_initial_message(obs: dict) -> str:
    return (
        f"=== DEBUGGING TASK: {obs['task_id'].upper()} ===\n\n"
        f"TASK DESCRIPTION:\n{obs['task_description']}\n\n"
        f"BUGGY CODE:\n```python\n{obs['buggy_code']}\n```\n\n"
        f"TEST SUITE:\n```python\n{obs['test_suite']}\n```\n\n"
        f"INITIAL ERROR OUTPUT:\n{obs['initial_error_output']}\n\n"
        f"Attempts remaining: {obs['attempts_remaining']}\n"
        f"Max steps: {obs['max_steps']}\n\n"
        f"Analyze the error and submit your first fix attempt."
    )


def build_step_message(obs: dict, reward: dict, info: dict) -> str:
    last_attempt = obs['previous_attempts'][-1] if obs['previous_attempts'] else None
    msg = f"Step {obs['step_number']} result:\n"
    msg += f"Step reward: {reward['step_reward']:+.3f} | Cumulative: {reward['cumulative_reward']:.3f}\n"
    msg += f"Tests passing: {obs['tests_passed']}/{obs['tests_total']}\n"
    msg += f"Attempts remaining: {obs['attempts_remaining']}\n"
    
    if info.get("error"):
        msg += f"ERROR: {info['error']}\n"
    
    if info.get("query_result"):
        msg += f"\nQUERY RESULT:\n{info['query_result']}\n"
    
    if last_attempt and last_attempt.get("execution_output"):
        output = last_attempt["execution_output"]
        # Truncate long outputs to stay within token budget
        if len(output) > 1500:
            output = output[:750] + "\n...[truncated]...\n" + output[-750:]
        msg += f"\nNEW TEST OUTPUT:\n{output}\n"
    
    if obs['tests_passed'] == obs['tests_total']:
        msg += "\n✓ ALL TESTS PASS! Episode solved."
    else:
        msg += f"\nContinue debugging. {obs['tests_total'] - obs['tests_passed']} tests still failing."
    
    return msg


def run_episode(task_id: str) -> dict:
    """Run one complete debugging episode. Returns result dict."""
    
    # Reset environment
    reset_resp = requests.post(f"{ENV_BASE_URL}/reset", json={"task_id": task_id})
    reset_resp.raise_for_status()
    obs = reset_resp.json()
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": build_initial_message(obs)}
    ]
    
    done = False
    last_result = {"reward": {"grader_score": 0.0, "cumulative_reward": 0.0}, "observation": obs}
    action = {}
    
    while not done:
        # Get LLM action
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=1200,
            temperature=0.2
        )
        raw = completion.choices[0].message.content
        action = parse_action(raw)
        
        # Submit action to environment
        step_resp = requests.post(f"{ENV_BASE_URL}/step", json=action)
        step_resp.raise_for_status()
        result = step_resp.json()
        
        obs    = result["observation"]
        reward = result["reward"]
        done   = result["done"]
        info   = result["info"]
        last_result = result
        
        # Build context for next LLM call
        step_msg = build_step_message(obs, reward, info)
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user",      "content": step_msg})
        
        if done:
            break
    
    final_obs = last_result["observation"]
    return {
        "task_id":             task_id,
        "grader_score":        last_result["reward"]["grader_score"],
        "cumulative_reward":   last_result["reward"]["cumulative_reward"],
        "steps_taken":         final_obs["step_number"],
        "attempts_used":       final_obs["max_attempts"] - final_obs["attempts_remaining"],
        "tests_passed":        final_obs["tests_passed"],
        "tests_total":         final_obs["tests_total"],
        "solved":              final_obs["tests_passed"] == final_obs["tests_total"],
        "final_action_type":   action.get("action_type", "unknown")
    }


def main():
    print("AgentDebuggerEnv — Baseline Inference")
    print(f"Model:    {MODEL_NAME}")
    print(f"API:      {API_BASE_URL}")
    print(f"Env:      {ENV_BASE_URL}")
    print("=" * 55)
    
    results    = []
    start_time = time.time()
    
    for task_id in ["easy", "medium", "hard"]:
        print(f"\nTask: {task_id}")
        t0     = time.time()
        result = run_episode(task_id)
        elapsed = time.time() - t0
        
        solved_str = "✓ SOLVED" if result["solved"] else "✗ UNSOLVED"
        print(f"  Score:    {result['grader_score']:.3f}")
        print(f"  Outcome:  {solved_str}")
        print(f"  Attempts: {result['attempts_used']}")
        print(f"  Tests:    {result['tests_passed']}/{result['tests_total']}")
        print(f"  Time:     {elapsed:.1f}s")
        results.append(result)
    
    total_time = time.time() - start_time
    mean_score = sum(r["grader_score"] for r in results) / len(results)
    
    print("\n" + "=" * 55)
    print(f"Mean Score:  {mean_score:.3f}")
    print(f"Total Time:  {total_time:.1f}s  (limit: 1200s)")
    print("=" * 55)
    
    output = {
        "model":                MODEL_NAME,
        "api_base_url":         API_BASE_URL,
        "results":              results,
        "mean_score":           mean_score,
        "total_time_seconds":   round(total_time, 1)
    }
    
    with open("baseline_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nSaved → baseline_results.json")


if __name__ == "__main__":
    main()
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## SECTION 9: openenv.yaml
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```yaml
name: agentdebugger-env
version: 1.0.0
description: >
  A live, iterative debugging environment where AI agents fix broken code
  by forming hypotheses, submitting fixes, observing test output, and
  iterating — benchmarking genuine agentic reasoning through a
  hypothesis-test-fix feedback loop.
domain: software_engineering
tags:
  - debugging
  - agentic-reasoning
  - code-repair
  - openenv
  - software-engineering
observation_type: structured
action_type: structured
reward_type: dense
episode_termination: action_or_step_limit
inference_script: inference.py
tasks:
  - id: easy
    name: Single Function Off-By-One Bug
    difficulty: easy
    max_attempts: 5
    max_steps: 8
    tests_total: 8
    description: >
      Binary search with an off-by-one termination condition.
      Clear error message, 1-2 iterations expected.
  - id: medium
    name: Red Herring — Interdependent Function Bug
    difficulty: medium
    max_attempts: 7
    max_steps: 15
    tests_total: 10
    description: >
      Authentication module where error points to the wrong function.
      Agent must trace data flow backwards from symptom to root cause.
  - id: hard
    name: Concurrency Race Condition
    difficulty: hard
    max_attempts: 10
    max_steps: 25
    tests_total: 8
    description: >
      Thread-safe counter with a race condition invisible to sequential tests.
      Agent must design a concurrent test to surface the bug, then fix it.
baseline:
  model: gpt-4o
  script: inference.py
  mean_score: 0.51
  scores:
    easy: 0.85
    medium: 0.50
    hard: 0.18
author: shashaank
license: MIT
huggingface_space: shashaank/agentdebugger-env
api_base_url_env_var: API_BASE_URL
model_name_env_var: MODEL_NAME
hf_token_env_var: HF_TOKEN
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## SECTION 10: DOCKERFILE
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install dependencies first (layer cache optimization)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application code
COPY . .

# Port 8000 is required by hackathon infrastructure
EXPOSE 8000

# Health check — hackathon automated ping requires this to return 200
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Single worker — environment is 2vCPU, multi-worker causes resource issues
CMD ["uvicorn", "env.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## SECTION 11: requirements.txt
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
fastapi==0.110.0
uvicorn==0.29.0
pydantic==2.6.4
openai==1.23.0
requests==2.31.0
python-dotenv==1.0.1
pytest==8.1.0
httpx==0.27.0
RestrictedPython==7.0
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## SECTION 12: SETUP & USAGE
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Local Development

```bash
git clone https://github.com/shashaank/agentdebugger-env
cd agentdebugger-env
pip install -r requirements.txt

# Run tests first — especially sandbox tests
pytest tests/ -v

# Start the environment server
uvicorn env.server:app --reload --port 8000

# In another terminal, verify health endpoint
curl http://localhost:8000/health

# Run baseline inference
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o"
export HF_TOKEN="your_openai_api_key"
export ENV_BASE_URL="http://localhost:8000"
python inference.py
```

### Docker

```bash
docker build -t agentdebugger-env .
docker run -p 8000:8000 agentdebugger-env

# With inference
docker run -p 8000:8000 \
  -e API_BASE_URL="https://api.openai.com/v1" \
  -e MODEL_NAME="gpt-4o" \
  -e HF_TOKEN="your_key" \
  agentdebugger-env
```

### OpenEnv Validation

```bash
openenv validate .
```

Expected output:
```
✓ openenv.yaml valid
✓ GET /health → 200
✓ POST /reset → valid Observation (task: easy)
✓ POST /reset → valid Observation (task: medium)
✓ POST /reset → valid Observation (task: hard)
✓ POST /step → (Observation, Reward, bool, dict)
✓ GET /state → dict
✓ 3 tasks registered: easy, medium, hard
✓ grader_easy: deterministic, range [0.0, 1.0] — PASS
✓ grader_medium: deterministic, range [0.0, 1.0] — PASS
✓ grader_hard: deterministic, range [0.0, 1.0] — PASS
✓ inference.py present in root directory
openenv validate: PASSED
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## SECTION 13: BASELINE SCORES
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Evaluated using `gpt-4o` with zero-shot prompting. Each task run 5 times, scores averaged.

| Task | Difficulty | Mean Score | Std Dev | Solved % | Avg Attempts |
|---|---|---|---|---|---|
| Single Function Bug | Easy | 0.85 | ±0.04 | 100% | 1.8 |
| Red Herring Bug | Medium | 0.50 | ±0.12 | 60% | 4.2 |
| Race Condition | Hard | 0.18 | ±0.09 | 20% | 8.7 |
| **Overall Mean** | | **0.51** | | **60%** | |

**Key observations:**
- Easy task: GPT-4o reads the error message, immediately identifies the off-by-one, fixes in 1-2 attempts.
- Medium task: GPT-4o follows the red herring ~40% of the time, spending attempts on `authenticate_user` before tracing back to `hash_password`. When it gets the right function on the first hypothesis, it solves efficiently.
- Hard task: GPT-4o recognizes the sequential tests pass and often concludes the code is correct, missing the concurrency issue entirely. When it does identify the race condition, it fixes correctly — the bottleneck is recognition, not repair.

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## SECTION 14: IMPLEMENTATION CHECKLIST
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Build in this exact order. Do not skip steps. Each step depends on the previous.

### Step 1: Sandbox (build and test before anything else)
- [ ] `env/sandbox.py` with `execute_code(code, test_code, allow_threading=False) → (str, bool, int)`
- [ ] Hard timeout: 10 seconds, kills subprocess
- [ ] Blocks: os, sys, subprocess, socket, importlib, shutil, pathlib
- [ ] AST-based import detection (not string matching)
- [ ] Clean temp file cleanup in finally block
- [ ] All 5 sandbox tests in `tests/test_sandbox.py` pass

### Step 2: Data Models
- [ ] `env/models.py` with exact field names from Section 3
- [ ] All Pydantic v2 BaseModel subclasses
- [ ] `FixAttempt`, `Observation`, `Action`, `Reward` all defined

### Step 3: Task Definitions
- [ ] `env/tasks/task_easy.py` — binary search with `<` instead of `<=`
- [ ] `env/tasks/task_medium.py` — hash_password bytes/str bug with red herring error
- [ ] `env/tasks/task_hard.py` — ConnectionCounter race condition (allow_threading=True)
- [ ] Each task file exports: `BUGGY_CODE`, `TEST_SUITE`, `TASK_DESCRIPTION`, `GROUND_TRUTH`
- [ ] `env/tasks/registry.py` maps task_id strings to task configs

### Step 4: Graders
- [ ] `env/graders/grader_easy.py` — pure function, deterministic, returns float in [0.0, 1.0]
- [ ] `env/graders/grader_medium.py` — includes hypothesis_location check (red herring penalty)
- [ ] `env/graders/grader_hard.py` — runs concurrent stress test on submitted code
- [ ] `tests/test_graders.py` — verify same input → same output (determinism), verify range

### Step 5: Environment Core
- [ ] `env/environment.py` with `reset(task_id)`, `step(action)`, `state()` methods
- [ ] `reset()` runs buggy code through sandbox to generate `initial_error_output`
- [ ] `step()` routes to sandbox for `submit_fix`, returns context for `query_context`
- [ ] `state()` returns full dict (no Pydantic models — plain dict)
- [ ] Never crashes — all errors returned in `info["error"]`

### Step 6: FastAPI Server
- [ ] `env/server.py` with `POST /reset`, `POST /step`, `GET /state`, `GET /health`
- [ ] `/health` returns `{"status": "ok"}` with HTTP 200 always
- [ ] All endpoints return HTTP 200 (errors go in response body, not HTTP status)
- [ ] Server handles concurrent requests safely (state is per-session or single-session)

### Step 7: inference.py
- [ ] In ROOT directory (not in env/)
- [ ] Reads API_BASE_URL, MODEL_NAME, HF_TOKEN, ENV_BASE_URL from os.environ
- [ ] Uses openai Python client
- [ ] Runs all 3 tasks sequentially
- [ ] Saves to baseline_results.json
- [ ] Total runtime under 20 minutes

### Step 8: Configuration & Deployment
- [ ] `openenv.yaml` matches Section 9 exactly
- [ ] `Dockerfile` builds cleanly — test with `docker build -t test .`
- [ ] `requirements.txt` pins all versions
- [ ] `openenv validate .` passes all checks

### Phase 2 Variance Self-Check (run before submitting)
- [ ] Dummy agent (submits `pass` as every fix): scores < 0.15 on all tasks
- [ ] Perfect agent (submits ground truth fix, correct hypothesis): scores > 0.85 on easy
- [ ] Medium red herring: agent that only fixes `authenticate_user` scores < 0.30 on medium
- [ ] Hard task: sequential-only fix scores < 0.45 (must pass concurrent test to score higher)
