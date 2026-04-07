"""
AgentDebuggerEnv Baseline Inference Script
==========================================
Baseline evaluation script for testing agent performance in the 
AgentDebugger environment.

System Configuration:
- API_BASE_URL: LLM API endpoint
- MODEL_NAME:   Model identifier for evaluation
- HF_TOKEN:     Authentication token
"""

import os
import json
import time
import re
import random
from openai import OpenAI, APIError, RateLimitError, APIConnectionError, APITimeoutError
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

Analyze the error output carefully and provide a corrected version of the complete code. 
You must always include a hypothesis explaining the root cause of the bug before 
submitting your fix. 

Guidelines:
- Submit complete source code files, not partial snippets or diffs.
- Incorporate all feedback from previous execution attempts.
- For concurrent tasks, ensure atomic operations and proper synchronization.
"""

# ── Robust API Completion Helper ──────────────────────────────────────────────

def get_completion(messages: list, model: str = MODEL_NAME, max_retries: int = 5) -> str:
    """Gets LLM completion with exponential backoff and retry logic."""
    for attempt in range(max_retries):
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1200,
                temperature=0.2,
                timeout=60.0  # Add a timeout to prevent hanging forever
            )
            return completion.choices[0].message.content
        except (RateLimitError, APIConnectionError, APITimeoutError) as e:
            if attempt == max_retries - 1:
                raise e
            wait_time = (2 ** attempt) + random.random()
            print(f"  [!] API Error ({type(e).__name__}). Retrying in {wait_time:.1f}s... (Attempt {attempt+1}/{max_retries})")
            time.sleep(wait_time)
        except APIError as e:
            # For general API errors, log and potentially retry if it's a 5xx
            print(f"  [!] OpenAI API Error: {e}")
            if attempt == max_retries - 1:
                raise e
            time.sleep(2)
        except Exception as e:
            print(f"  [!] Unexpected error during completion: {e}")
            raise e
    return ""


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
        # Get LLM action using the robust helper
        try:
            raw = get_completion(messages)
            if not raw:
                raise ValueError("Empty response from LLM")
            action = parse_action(raw)
        except Exception as e:
            print(f"  [✗] Failed to get response from LLM after retries: {e}")
            # Fallback action to avoid crashing the whole episode
            action = {
                "action_type": "give_up",
                "final_diagnosis": f"Inference system failure: {str(e)}"
            }
            raw = json.dumps(action)

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
    
    # ── Environment validation ────────────────────────────────────────────────
    has_token = bool(HF_TOKEN and len(HF_TOKEN) > 5)
    masked_token = f"{HF_TOKEN[:4]}...{HF_TOKEN[-4:]}" if has_token else "MISSING"
    
    print(f"Model:    {MODEL_NAME}")
    print(f"API:      {API_BASE_URL}")
    print(f"Token:    {masked_token}")
    print(f"Env:      {ENV_BASE_URL}")
    
    if not has_token and "openai.com" in API_BASE_URL:
        print("WARNING: HF_TOKEN is missing but using default OpenAI endpoint. This may fail.")
    
    print("=" * 55)

    results    = []
    start_time = time.time()

    for task_id in ["easy", "medium", "hard"]:
        print(f"\nTask: {task_id}")
        t0     = time.time()
        try:
            result = run_episode(task_id)
        except Exception as e:
            print(f"  [✗] Error running episode '{task_id}': {e}")
            result = {
                "task_id": task_id,
                "grader_score": 0.0,
                "cumulative_reward": 0.0,
                "steps_taken": 0,
                "attempts_used": 0,
                "tests_passed": 0,
                "tests_total": 0,
                "solved": False,
                "final_action_type": "error"
            }
        
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
