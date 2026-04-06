# """
# Grader Hard — Concurrent stress test scoring.
# Custom weights:
#   0.40 — original 8 tests pass
#   0.30 — concurrent stress test (1000 threads)
#   0.20 — hypothesis accuracy
#   0.10 — efficiency bonus (solved within 5 attempts)
# """

# import threading
# from typing import List, Dict, Any
# from env.graders.base_grader import BaseGrader


# class HardGrader(BaseGrader):

#     def _run_concurrent_stress_test(self, code: str) -> bool:
#         """
#         Run a 1000-thread concurrent stress test against the submitted code.
#         Returns True if the counter ends at exactly 1000 after 1000 concurrent increments.
#         """
#         try:
#             # Execute the code in an isolated namespace
#             namespace = {}
#             exec(code, namespace)

#             CounterClass = namespace.get("ConnectionCounter")
#             if CounterClass is None:
#                 return False

#             counter = CounterClass()
#             num_threads = 1000

#             threads = [
#                 threading.Thread(target=counter.increment)
#                 for _ in range(num_threads)
#             ]
#             for t in threads:
#                 t.start()
#             for t in threads:
#                 t.join(timeout=10)

#             return counter.get_count() == num_threads
#         except Exception:
#             return False

#     def score(
#         self,
#         task_config: dict,
#         attempts: List[Dict[str, Any]],
#         best_tests_passed: int,
#         tests_total: int,
#         attempts_used: int,
#         max_attempts: int,
#         hypotheses: List[str],
#     ) -> float:
#         ground_truth = task_config["ground_truth"]
#         keywords = ground_truth["hypothesis_keywords"]

#         # 1. Original tests pass (weight: 0.40)
#         test_pass_ratio = (best_tests_passed / tests_total) if tests_total > 0 else 0.0
#         original_test_score = test_pass_ratio * 0.40

#         # 2. Concurrent stress test (weight: 0.30)
#         # Use the best attempt's code (highest tests_passed, then latest)
#         concurrent_score = 0.0
#         if attempts:
#             # Find the best attempt
#             best_attempt = max(
#                 attempts,
#                 key=lambda a: (a.get("tests_passed", 0), a.get("attempt_number", 0))
#             )
#             best_code = best_attempt.get("code_submitted", "")
#             if best_code:
#                 # Run the stress test 3 times — must pass all 3 for full credit
#                 passes = sum(
#                     1 for _ in range(3)
#                     if self._run_concurrent_stress_test(best_code)
#                 )
#                 if passes == 3:
#                     concurrent_score = 0.30
#                 elif passes >= 1:
#                     concurrent_score = 0.15  # Partial — inconsistent fix

#         # 3. Hypothesis accuracy (weight: 0.20)
#         if hypotheses:
#             matches = sum(
#                 1 for h in hypotheses
#                 if self._check_hypothesis_keywords(h, keywords, "any")
#             )
#             hypothesis_ratio = matches / len(hypotheses)
#         else:
#             hypothesis_ratio = 0.0
#         hypothesis_score = hypothesis_ratio * 0.20

#         # 4. Efficiency bonus (weight: 0.10)
#         efficiency_score = 0.10 if attempts_used <= 5 else 0.0

#         total = original_test_score + concurrent_score + hypothesis_score + efficiency_score
#         return self._clamp(total)


"""
Grader Hard — Concurrent stress test scoring.

Weights:
  0.40 — agent's submitted fix passes the original 8 sequential tests
  0.30 — agent's submitted fix passes a 1000-thread concurrent stress test
  0.20 — hypothesis accuracy (agent correctly identified race condition)
  0.10 — efficiency bonus (solved within 5 attempts)

Security: ALL code execution goes through execute_code() sandbox.
          Never uses raw exec() or eval() on agent-submitted code.

Score floor fix: original_test_score uses only agent-submitted attempts,
                 NOT the initial buggy code. An agent that submits nothing
                 scores 0.0, not 0.40.
"""

from typing import List, Dict, Any
from env.graders.base_grader import BaseGrader
from env.sandbox import execute_code


# The concurrent stress test — written as a string and run through the sandbox.
# 1000 threads all calling increment() simultaneously.
# A correct fix must result in count == 1000 every single time.
_CONCURRENT_STRESS_TEST = """
import threading

counter = ConnectionCounter()
num_threads = 1000

threads = [threading.Thread(target=counter.increment) for _ in range(num_threads)]
for t in threads:
    t.start()
for t in threads:
    t.join()

result = counter.get_count()
assert result == num_threads, f"CONCURRENT FAIL: expected {num_threads}, got {result}"
print(f"CONCURRENT PASS: {result} == {num_threads}")
"""
class HardGrader(BaseGrader):

    def _run_concurrent_stress_test(self, code: str) -> bool:
        """
        Run the concurrent stress test against agent-submitted code.
        Routes through execute_code() sandbox — never uses raw exec().
        Returns True only if the counter reaches exactly 1000 after
        1000 concurrent increments.
        """
        output, timed_out, _ = execute_code(
            code,
            _CONCURRENT_STRESS_TEST,
            allow_threading=True,
        )
        if timed_out:
            return False
        return "CONCURRENT PASS" in output and "CONCURRENT FAIL" not in output

    def score(
        self,
        task_config: dict,
        attempts: List[Dict[str, Any]],
        best_tests_passed: int,
        tests_total: int,
        attempts_used: int,
        max_attempts: int,
        hypotheses: List[str],
    ) -> float:
        ground_truth = task_config["ground_truth"]
        keywords = ground_truth["hypothesis_keywords"]

        # ── 1. Sequential test score (weight: 0.40) ──────────────────────────
        # IMPORTANT: Only count agent-submitted attempts, NOT the initial buggy
        # code. The buggy code passes all 8 sequential tests — if we used
        # best_tests_passed from environment state, every agent would score
        # 0.40 for free without fixing anything. We recalculate from attempts.
        if attempts:
            agent_best_sequential = max(
                a.get("tests_passed", 0) for a in attempts
            )
        else:
            agent_best_sequential = 0  # No attempts submitted → 0.0

        sequential_ratio = agent_best_sequential / tests_total if tests_total > 0 else 0.0
        sequential_score = sequential_ratio * 0.40

        # ── 2. Concurrent stress test (weight: 0.30) ──────────────────────────
        # Use the best attempt by sequential test count (ties broken by recency).
        # Run the stress test 3 times — must pass all 3 for full credit,
        # at least 1 for partial credit. This handles non-determinism fairly.
        concurrent_score = 0.0
        if attempts:
            best_attempt = max(
                attempts,
                key=lambda a: (a.get("tests_passed", 0), a.get("attempt_number", 0))
            )
            best_code = best_attempt.get("code_submitted", "").strip()

            if best_code:
                passes = sum(
                    1 for _ in range(3)
                    if self._run_concurrent_stress_test(best_code)
                )
                if passes == 3:
                    concurrent_score = 0.30       # Fully correct fix
                elif passes >= 1:
                    concurrent_score = 0.15       # Partially correct — inconsistent

        # ── 3. Hypothesis accuracy (weight: 0.20) ─────────────────────────────
        if hypotheses:
            matches = sum(
                1 for h in hypotheses
                if self._check_hypothesis_keywords(h, keywords, "any")
            )
            hypothesis_ratio = matches / len(hypotheses)
        else:
            hypothesis_ratio = 0.0
        hypothesis_score = hypothesis_ratio * 0.20

        # ── 4. Efficiency bonus (weight: 0.10) ────────────────────────────────
        # Only awarded if the agent actually fixed the concurrent bug too,
        # not just for submitting fewer attempts on a wrong fix.
        efficiency_score = 0.10 if (concurrent_score == 0.30 and attempts_used <= 5) else 0.0

        total = sequential_score + concurrent_score + hypothesis_score + efficiency_score
        return self._clamp(total)