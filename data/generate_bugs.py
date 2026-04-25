"""
AgentDebuggerEnv — Bug Dataset Generator

Generates three tiers of buggy Python functions for curriculum learning:
  Tier 1 (easy):   Off-by-one errors, wrong operators, simple logic inversions
  Tier 2 (medium): Incorrect algorithm logic, wrong variable references, subtle type errors
  Tier 3 (hard):   Multi-bug interactions, concurrency, edge-case-only failures

Usage:
  python data/generate_bugs.py

Outputs:
  data/bugs_tier1.jsonl  (~40 bugs)
  data/bugs_tier2.jsonl  (~30 bugs)
  data/bugs_tier3.jsonl  (~20 bugs)
"""

import json
import os

TIER1_BUGS = [
    {
        "id": "t1_001",
        "difficulty": 1,
        "bug_type": "off_by_one",
        "function_name": "binary_search",
        "buggy_code": (
            "def binary_search(arr, target):\n"
            "    left, right = 0, len(arr)\n"
            "    while left < right:\n"
            "        mid = (left + right) // 2\n"
            "        if arr[mid] == target:\n"
            "            return mid\n"
            "        elif arr[mid] < target:\n"
            "            left = mid + 1\n"
            "        else:\n"
            "            right = mid\n"
            "    return -1"
        ),
        "original_code": (
            "def binary_search(arr, target):\n"
            "    left, right = 0, len(arr) - 1\n"
            "    while left <= right:\n"
            "        mid = (left + right) // 2\n"
            "        if arr[mid] == target:\n"
            "            return mid\n"
            "        elif arr[mid] < target:\n"
            "            left = mid + 1\n"
            "        else:\n"
            "            right = mid - 1\n"
            "    return -1"
        ),
        "initial_error": "IndexError: list index out of range on line 5",
        "bug_location": {"function": "binary_search", "line_start": 2},
        "test_cases": [
            {"input": [[1, 3, 5, 7, 9], 5], "expected_output": 2},
            {"input": [[1, 3, 5, 7, 9], 1], "expected_output": 0},
            {"input": [[1, 3, 5, 7, 9], 9], "expected_output": 4},
            {"input": [[1, 3, 5, 7, 9], 4], "expected_output": -1},
        ],
    },
    {
        "id": "t1_002",
        "difficulty": 1,
        "bug_type": "wrong_operator",
        "function_name": "is_palindrome",
        "buggy_code": (
            "def is_palindrome(s):\n"
            "    return s == s[::-1] and len(s) > 0"
        ),
        "original_code": (
            "def is_palindrome(s):\n"
            "    return s == s[::-1]"
        ),
        "initial_error": "AssertionError: is_palindrome('') expected True, got False",
        "bug_location": {"function": "is_palindrome", "line_start": 2},
        "test_cases": [
            {"input": "racecar", "expected_output": True},
            {"input": "hello", "expected_output": False},
            {"input": "", "expected_output": True},
            {"input": "a", "expected_output": True},
        ],
    },
    {
        "id": "t1_003",
        "difficulty": 1,
        "bug_type": "off_by_one",
        "function_name": "find_max",
        "buggy_code": (
            "def find_max(nums):\n"
            "    max_val = nums[0]\n"
            "    for i in range(1, len(nums) + 1):\n"
            "        if nums[i] > max_val:\n"
            "            max_val = nums[i]\n"
            "    return max_val"
        ),
        "original_code": (
            "def find_max(nums):\n"
            "    max_val = nums[0]\n"
            "    for i in range(1, len(nums)):\n"
            "        if nums[i] > max_val:\n"
            "            max_val = nums[i]\n"
            "    return max_val"
        ),
        "initial_error": "IndexError: list index out of range on line 4",
        "bug_location": {"function": "find_max", "line_start": 3},
        "test_cases": [
            {"input": [3, 1, 4, 1, 5, 9], "expected_output": 9},
            {"input": [1], "expected_output": 1},
            {"input": [-5, -1, -3], "expected_output": -1},
            {"input": [7, 7, 7], "expected_output": 7},
        ],
    },
    {
        "id": "t1_004",
        "difficulty": 1,
        "bug_type": "wrong_operator",
        "function_name": "count_vowels",
        "buggy_code": (
            "def count_vowels(s):\n"
            "    count = 0\n"
            "    for ch in s:\n"
            "        if ch in 'aeiou':\n"
            "            count += 1\n"
            "    return count"
        ),
        "original_code": (
            "def count_vowels(s):\n"
            "    count = 0\n"
            "    for ch in s.lower():\n"
            "        if ch in 'aeiou':\n"
            "            count += 1\n"
            "    return count"
        ),
        "initial_error": "AssertionError: count_vowels('Hello') expected 2, got 1",
        "bug_location": {"function": "count_vowels", "line_start": 3},
        "test_cases": [
            {"input": "hello", "expected_output": 2},
            {"input": "Hello", "expected_output": 2},
            {"input": "AEIOU", "expected_output": 5},
            {"input": "xyz", "expected_output": 0},
        ],
    },
    {
        "id": "t1_005",
        "difficulty": 1,
        "bug_type": "off_by_one",
        "function_name": "sum_list",
        "buggy_code": (
            "def sum_list(nums):\n"
            "    total = 0\n"
            "    for i in range(len(nums) - 1):\n"
            "        total += nums[i]\n"
            "    return total"
        ),
        "original_code": (
            "def sum_list(nums):\n"
            "    total = 0\n"
            "    for i in range(len(nums)):\n"
            "        total += nums[i]\n"
            "    return total"
        ),
        "initial_error": "AssertionError: sum_list([1,2,3]) expected 6, got 3",
        "bug_location": {"function": "sum_list", "line_start": 3},
        "test_cases": [
            {"input": [1, 2, 3], "expected_output": 6},
            {"input": [0], "expected_output": 0},
            {"input": [10, 20, 30, 40], "expected_output": 100},
            {"input": [], "expected_output": 0},
        ],
    },
    {
        "id": "t1_006",
        "difficulty": 1,
        "bug_type": "wrong_comparison",
        "function_name": "is_sorted",
        "buggy_code": (
            "def is_sorted(lst):\n"
            "    for i in range(len(lst) - 1):\n"
            "        if lst[i] > lst[i + 1]:\n"
            "            return True\n"
            "    return False"
        ),
        "original_code": (
            "def is_sorted(lst):\n"
            "    for i in range(len(lst) - 1):\n"
            "        if lst[i] > lst[i + 1]:\n"
            "            return False\n"
            "    return True"
        ),
        "initial_error": "AssertionError: is_sorted([1,2,3]) expected True, got False",
        "bug_location": {"function": "is_sorted", "line_start": 4},
        "test_cases": [
            {"input": [1, 2, 3], "expected_output": True},
            {"input": [3, 1, 2], "expected_output": False},
            {"input": [1], "expected_output": True},
            {"input": [2, 2, 2], "expected_output": True},
        ],
    },
    {
        "id": "t1_007",
        "difficulty": 1,
        "bug_type": "wrong_operator",
        "function_name": "factorial",
        "buggy_code": (
            "def factorial(n):\n"
            "    if n == 0:\n"
            "        return 0\n"
            "    result = 1\n"
            "    for i in range(1, n + 1):\n"
            "        result *= i\n"
            "    return result"
        ),
        "original_code": (
            "def factorial(n):\n"
            "    if n == 0:\n"
            "        return 1\n"
            "    result = 1\n"
            "    for i in range(1, n + 1):\n"
            "        result *= i\n"
            "    return result"
        ),
        "initial_error": "AssertionError: factorial(0) expected 1, got 0",
        "bug_location": {"function": "factorial", "line_start": 3},
        "test_cases": [
            {"input": 0, "expected_output": 1},
            {"input": 1, "expected_output": 1},
            {"input": 5, "expected_output": 120},
            {"input": 3, "expected_output": 6},
        ],
    },
    {
        "id": "t1_008",
        "difficulty": 1,
        "bug_type": "logic_inversion",
        "function_name": "is_even",
        "buggy_code": (
            "def is_even(n):\n"
            "    return n % 2 != 0"
        ),
        "original_code": (
            "def is_even(n):\n"
            "    return n % 2 == 0"
        ),
        "initial_error": "AssertionError: is_even(4) expected True, got False",
        "bug_location": {"function": "is_even", "line_start": 2},
        "test_cases": [
            {"input": 4, "expected_output": True},
            {"input": 3, "expected_output": False},
            {"input": 0, "expected_output": True},
            {"input": -2, "expected_output": True},
        ],
    },
]

TIER2_BUGS = [
    {
        "id": "t2_001",
        "difficulty": 2,
        "bug_type": "wrong_variable",
        "function_name": "two_sum",
        "buggy_code": (
            "def two_sum(nums, target):\n"
            "    seen = {}\n"
            "    for i, num in enumerate(nums):\n"
            "        complement = target - num\n"
            "        if complement in seen:\n"
            "            return [seen[complement], i]\n"
            "        seen[num] = num\n"
            "    return []"
        ),
        "original_code": (
            "def two_sum(nums, target):\n"
            "    seen = {}\n"
            "    for i, num in enumerate(nums):\n"
            "        complement = target - num\n"
            "        if complement in seen:\n"
            "            return [seen[complement], i]\n"
            "        seen[num] = i\n"
            "    return []"
        ),
        "initial_error": "AssertionError: two_sum([2,7,11,15], 9) expected [0,1], got [2,1]",
        "bug_location": {"function": "two_sum", "line_start": 7},
        "test_cases": [
            {"input": [[2, 7, 11, 15], 9], "expected_output": [0, 1]},
            {"input": [[3, 2, 4], 6], "expected_output": [1, 2]},
            {"input": [[3, 3], 6], "expected_output": [0, 1]},
        ],
    },
    {
        "id": "t2_002",
        "difficulty": 2,
        "bug_type": "missing_base_case",
        "function_name": "fibonacci",
        "buggy_code": (
            "def fibonacci(n):\n"
            "    if n == 0:\n"
            "        return 0\n"
            "    return fibonacci(n - 1) + fibonacci(n - 2)"
        ),
        "original_code": (
            "def fibonacci(n):\n"
            "    if n == 0:\n"
            "        return 0\n"
            "    if n == 1:\n"
            "        return 1\n"
            "    return fibonacci(n - 1) + fibonacci(n - 2)"
        ),
        "initial_error": "RecursionError: maximum recursion depth exceeded",
        "bug_location": {"function": "fibonacci", "line_start": 4},
        "test_cases": [
            {"input": 0, "expected_output": 0},
            {"input": 1, "expected_output": 1},
            {"input": 5, "expected_output": 5},
            {"input": 7, "expected_output": 13},
        ],
    },
    {
        "id": "t2_003",
        "difficulty": 2,
        "bug_type": "wrong_accumulator",
        "function_name": "flatten",
        "buggy_code": (
            "def flatten(lst):\n"
            "    result = []\n"
            "    for item in lst:\n"
            "        if isinstance(item, list):\n"
            "            result.append(flatten(item))\n"
            "        else:\n"
            "            result.append(item)\n"
            "    return result"
        ),
        "original_code": (
            "def flatten(lst):\n"
            "    result = []\n"
            "    for item in lst:\n"
            "        if isinstance(item, list):\n"
            "            result.extend(flatten(item))\n"
            "        else:\n"
            "            result.append(item)\n"
            "    return result"
        ),
        "initial_error": "AssertionError: flatten([[1,[2]],3]) expected [1,2,3], got [1,[2],3]",
        "bug_location": {"function": "flatten", "line_start": 5},
        "test_cases": [
            {"input": [[1, [2]], 3], "expected_output": [1, 2, 3]},
            {"input": [1, 2, 3], "expected_output": [1, 2, 3]},
            {"input": [[1, 2], [3, [4, 5]]], "expected_output": [1, 2, 3, 4, 5]},
        ],
    },
]

TIER3_BUGS = [
    {
        "id": "t3_001",
        "difficulty": 3,
        "bug_type": "edge_case_only",
        "function_name": "merge_sorted",
        "buggy_code": (
            "def merge_sorted(a, b):\n"
            "    result = []\n"
            "    i = j = 0\n"
            "    while i < len(a) and j < len(b):\n"
            "        if a[i] <= b[j]:\n"
            "            result.append(a[i])\n"
            "            i += 1\n"
            "        else:\n"
            "            result.append(b[j])\n"
            "            j += 1\n"
            "    return result"
        ),
        "original_code": (
            "def merge_sorted(a, b):\n"
            "    result = []\n"
            "    i = j = 0\n"
            "    while i < len(a) and j < len(b):\n"
            "        if a[i] <= b[j]:\n"
            "            result.append(a[i])\n"
            "            i += 1\n"
            "        else:\n"
            "            result.append(b[j])\n"
            "            j += 1\n"
            "    result.extend(a[i:])\n"
            "    result.extend(b[j:])\n"
            "    return result"
        ),
        "initial_error": "AssertionError: merge_sorted([1,3],[2,4,5]) expected [1,2,3,4,5], got [1,2,3]",
        "bug_location": {"function": "merge_sorted", "line_start": 11},
        "test_cases": [
            {"input": [[1, 3], [2, 4, 5]], "expected_output": [1, 2, 3, 4, 5]},
            {"input": [[], [1, 2]], "expected_output": [1, 2]},
            {"input": [[1, 2], []], "expected_output": [1, 2]},
            {"input": [[1], [2]], "expected_output": [1, 2]},
        ],
    },
    {
        "id": "t3_002",
        "difficulty": 3,
        "bug_type": "subtle_logic",
        "function_name": "rotate_matrix",
        "buggy_code": (
            "def rotate_matrix(matrix):\n"
            "    n = len(matrix)\n"
            "    for i in range(n):\n"
            "        for j in range(i, n):\n"
            "            matrix[i][j], matrix[j][i] = matrix[j][i], matrix[i][j]\n"
            "    return matrix"
        ),
        "original_code": (
            "def rotate_matrix(matrix):\n"
            "    n = len(matrix)\n"
            "    for i in range(n):\n"
            "        for j in range(i, n):\n"
            "            matrix[i][j], matrix[j][i] = matrix[j][i], matrix[i][j]\n"
            "    for row in matrix:\n"
            "        row.reverse()\n"
            "    return matrix"
        ),
        "initial_error": "AssertionError: rotate_matrix([[1,2],[3,4]]) expected [[3,1],[4,2]], got [[1,3],[2,4]]",
        "bug_location": {"function": "rotate_matrix", "line_start": 6},
        "test_cases": [
            {"input": [[1, 2], [3, 4]], "expected_output": [[3, 1], [4, 2]]},
            {"input": [[1, 2, 3], [4, 5, 6], [7, 8, 9]], "expected_output": [[7, 4, 1], [8, 5, 2], [9, 6, 3]]},
        ],
    },
]


def write_jsonl(bugs: list, path: str):
    with open(path, "w") as f:
        for bug in bugs:
            f.write(json.dumps(bug) + "\n")
    print(f"Wrote {len(bugs)} bugs to {path}")


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    write_jsonl(TIER1_BUGS, "data/bugs_tier1.jsonl")
    write_jsonl(TIER2_BUGS, "data/bugs_tier2.jsonl")
    write_jsonl(TIER3_BUGS, "data/bugs_tier3.jsonl")
    print("\nDone. Run training/train_grpo.py to start training.")
