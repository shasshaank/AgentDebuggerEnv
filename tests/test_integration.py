"""
AgentDebuggerEnv — Integration Tests
====================================
Verifies the full episode lifecycle: reset -> step -> end.
Assumes the server is available via the DebuggerEnvironment class directly
(testing the logic, not the HTTP layer which is just a thin wrapper).
"""

import pytest
from env.environment import DebuggerEnvironment
from env.models import Action

def test_full_episode_easy():
    """Test a full successful episode on the 'easy' task."""
    env = DebuggerEnvironment()
    
    # 1. Reset
    obs = env.reset("easy")
    assert obs["task_id"] == "easy"
    assert obs["done"] is False
    assert obs["tests_passed"] < obs["tests_total"]
    
    # 2. Submit a fix (using known ground truth)
    # The easy task is binary search with 'left < right' instead of 'left <= right'
    ground_truth_code = """
def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
"""
    action = Action(
        action_type="submit_fix",
        fixed_code=ground_truth_code,
        hypothesis="Binary search termination condition should be left <= right to include all elements."
    )
    
    result = env.step(action)
    
    # 3. Verify results
    assert result["done"] is True
    assert result["observation"]["tests_passed"] == result["observation"]["tests_total"]
    assert result["reward"]["grader_score"] > 0.80

def test_query_hint_system():
    """Test the newly added hint system."""
    env = DebuggerEnvironment()
    env.reset("hard")
    
    action = Action(
        action_type="query_context",
        query_type="test_suggestion"
    )
    
    result = env.step(action)
    assert "concurrent threads" in result["info"]["query_result"]
    assert result["reward"]["step_reward"] == 0.0  # First query is free

def test_hard_grader_consensus():
    """
    Test that the hard grader runs multiple times.
    (We mock execute_code to simulate flakiness).
    """
    from unittest.mock import patch
    from env.graders.grader_hard import HardGrader
    
    grader = HardGrader()
    
    # Mock execute_code to return success 3/5 times
    # Sequence: PASS, FAIL, PASS, FAIL, PASS
    with patch("env.graders.grader_hard.execute_code") as mock_exec:
        mock_exec.side_effect = [
            ("CONCURRENT PASS", False, 100),
            ("CONCURRENT FAIL", False, 100),
            ("CONCURRENT PASS", False, 100),
            ("CONCURRENT FAIL", False, 100),
            ("CONCURRENT PASS", False, 100),
        ]
        
        score = grader.score(
            task_config={"task_id": "hard", "ground_truth": {"hypothesis_keywords": ["race"]}},
            attempts=[{"tests_passed": 8, "attempt_number": 1, "code_submitted": "..."}],
            best_tests_passed=8,
            tests_total=8,
            attempts_used=1,
            max_attempts=10,
            hypotheses=["race condition"]
        )
        
        # 3/5 passes → should get partial credit (0.15) for concurrency
        # Sequential: 1.0 * 0.40 = 0.40
        # Concurrency: 0.15
        # Hypothesis: 1.0 * 0.20 = 0.20
        # Efficiency: (concurrent_score == 0.30) is False -> 0.0
        # Total: 0.75
        assert score == 0.75
