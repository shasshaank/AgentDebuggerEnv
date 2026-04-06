"""
AgentDebuggerEnv — Pydantic Data Models
========================================
All models are Pydantic v2 BaseModel subclasses with exact field names
required by the OpenEnv spec and hackathon validation pipeline.
"""

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
    test_suite: str               # The full test suite code
    initial_error_output: str     # Output of running the test suite against the buggy code at reset()

    # Dynamic state — changes each step
    current_code: str             # The most recent version of the code
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


class Action(BaseModel):
    action_type: str              # "submit_fix" | "query_context" | "give_up"

    # ── submit_fix ──
    fixed_code: Optional[str] = None
    hypothesis: Optional[str] = None

    # ── query_context ──
    query_type: Optional[str] = None
    query_target: Optional[str] = None

    # ── give_up ──
    final_diagnosis: Optional[str] = None


class Reward(BaseModel):
    step_reward: float            # Reward for THIS step only. Range: -1.0 to +1.0
    cumulative_reward: float      # Sum of all step_rewards this episode
    grader_score: float           # 0.0 during episode. Set ONLY on terminal step (done=True).
    breakdown: Dict[str, float]   # Itemized components
