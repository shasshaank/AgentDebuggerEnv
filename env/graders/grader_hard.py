"""
Grader Hard — Concurrent stress test scoring.
Custom weights:
  0.40 — original 8 tests pass
  0.30 — concurrent stress test (1000 threads)
  0.20 — hypothesis accuracy
  0.10 — efficiency bonus (solved within 5 attempts)
"""

import threading
from typing import List, Dict, Any
from env.graders.base_grader import BaseGrader


class HardGrader(BaseGrader):

    def _run_concurrent_stress_test(self, code: str) -> bool:
        """
        Run a 1000-thread concurrent stress test against the submitted code.
        Returns True if the counter ends at exactly 1000 after 1000 concurrent increments.
        """
        try:
            # Execute the code in an isolated namespace
            namespace = {}
            exec(code, namespace)

            CounterClass = namespace.get("ConnectionCounter")
            if CounterClass is None:
                return False

            counter = CounterClass()
            num_threads = 1000

            threads = [
                threading.Thread(target=counter.increment)
                for _ in range(num_threads)
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10)

            return counter.get_count() == num_threads
        except Exception:
            return False

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

        # 1. Original tests pass (weight: 0.40)
        test_pass_ratio = (best_tests_passed / tests_total) if tests_total > 0 else 0.0
        original_test_score = test_pass_ratio * 0.40

        # 2. Concurrent stress test (weight: 0.30)
        # Use the best attempt's code (highest tests_passed, then latest)
        concurrent_score = 0.0
        if attempts:
            # Find the best attempt
            best_attempt = max(
                attempts,
                key=lambda a: (a.get("tests_passed", 0), a.get("attempt_number", 0))
            )
            best_code = best_attempt.get("code_submitted", "")
            if best_code:
                # Run the stress test 3 times — must pass all 3 for full credit
                passes = sum(
                    1 for _ in range(3)
                    if self._run_concurrent_stress_test(best_code)
                )
                if passes == 3:
                    concurrent_score = 0.30
                elif passes >= 1:
                    concurrent_score = 0.15  # Partial — inconsistent fix

        # 3. Hypothesis accuracy (weight: 0.20)
        if hypotheses:
            matches = sum(
                1 for h in hypotheses
                if self._check_hypothesis_keywords(h, keywords, "any")
            )
            hypothesis_ratio = matches / len(hypotheses)
        else:
            hypothesis_ratio = 0.0
        hypothesis_score = hypothesis_ratio * 0.20

        # 4. Efficiency bonus (weight: 0.10)
        efficiency_score = 0.10 if attempts_used <= 5 else 0.0

        total = original_test_score + concurrent_score + hypothesis_score + efficiency_score
        return self._clamp(total)
