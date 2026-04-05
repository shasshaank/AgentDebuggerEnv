"""
Tests for the code execution sandbox.
All 5 tests are required by the hackathon spec.
"""

import pytest
from env.sandbox import execute_code


def test_timeout_enforcement():
    """Code with infinite loop must return timed_out=True within ~11 seconds."""
    code = "while True: pass"
    output, timed_out, elapsed_ms = execute_code(code, "")
    assert timed_out is True
    assert "TIMEOUT" in output or "timeout" in output.lower()


def test_os_import_blocked():
    """os module must be blocked — cannot execute system commands."""
    code = "import os; os.system('echo pwned')"
    output, timed_out, _ = execute_code(code, "")
    assert "pwned" not in output
    assert "BLOCKED" in output or "blocked" in output.lower()


def test_sys_import_blocked():
    """sys module must be blocked."""
    code = "import sys; sys.exit(0)"
    output, _, _ = execute_code(code, "")
    assert "blocked" in output.lower() or "import" in output.lower()


def test_clean_code_runs():
    """Clean, safe code with tests must execute correctly."""
    code = "def add(a, b): return a + b"
    test = "assert add(2, 3) == 5\nprint('PASSED')"
    output, timed_out, _ = execute_code(code, test)
    assert "PASSED" in output
    assert timed_out is False


def test_syntax_error_returns_output():
    """Code with syntax errors should return the SyntaxError, not crash."""
    code = "def broken(: pass"
    output, timed_out, _ = execute_code(code, "")
    assert "SyntaxError" in output
    assert timed_out is False


# ── Additional robustness tests ──────────────────────────────────────────────

def test_subprocess_import_blocked():
    """subprocess module must be blocked."""
    code = "import subprocess; subprocess.run(['echo', 'pwned'])"
    output, _, _ = execute_code(code, "")
    assert "pwned" not in output
    assert "BLOCKED" in output or "blocked" in output.lower()


def test_threading_blocked_by_default():
    """threading must be blocked unless allow_threading=True."""
    code = "import threading; print('thread imported')"
    output, _, _ = execute_code(code, "")
    assert "thread imported" not in output
    assert "BLOCKED" in output or "blocked" in output.lower()


def test_threading_allowed_when_flagged():
    """threading must be allowed when allow_threading=True."""
    code = "import threading; print('thread imported')"
    output, _, _ = execute_code(code, "", allow_threading=True)
    assert "thread imported" in output


def test_from_import_blocked():
    """'from os import path' style imports must also be blocked."""
    code = "from os import path; print('pwned')"
    output, _, _ = execute_code(code, "")
    assert "pwned" not in output
    assert "BLOCKED" in output or "blocked" in output.lower()


def test_no_state_leak_between_executions():
    """Each execution must be completely isolated — no shared state."""
    code1 = "shared_var = 42"
    output1, _, _ = execute_code(code1, "print('set')")
    assert "set" in output1

    code2 = ""
    test2 = "try:\\n    print(shared_var)\\nexcept NameError:\\n    print('ISOLATED')"
    # Fix: use actual newlines
    code2_test = "try:\n    print(shared_var)\nexcept NameError:\n    print('ISOLATED')"
    output2, _, _ = execute_code("", code2_test)
    assert "ISOLATED" in output2
