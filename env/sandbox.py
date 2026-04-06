"""
AgentDebuggerEnv — Sandboxed Code Execution
============================================
ALL code execution in the environment must go through execute_code().
Never call exec() or subprocess directly anywhere else.

Security measures:
  1. Hard execution timeout (10 seconds)
  2. AST-based import blocking (not string matching)
  3. Subprocess isolation
  4. Clean temp file cleanup in finally block
  5. Fresh namespace per attempt (no state leaks)
"""

import subprocess
import tempfile
import os
import time
import ast
from typing import Tuple

BLOCKED_IMPORTS = [
    "os", "sys", "subprocess", "socket", "importlib", "shutil",
    "pathlib", "glob", "pickle", "shelve", "dbm", "sqlite3",
    "ftplib", "http", "urllib", "requests", "httpx", "asyncio",
    "multiprocessing", "threading",
    "ctypes", "cffi", "resource", "signal", "mmap", "gc"
]

EXECUTION_TIMEOUT_SECONDS = 10
MEMORY_LIMIT_MB = 256


def _build_import_checker(blocked: list[str]) -> str:
    """Build a Python script snippet that checks for blocked imports using AST parsing."""
    blocked_repr = repr(blocked)
    return f'''
import ast as _ast
import sys as _sys

_BLOCKED = {blocked_repr}
_source_to_check = open(__file__).read()

# Find the marker line and only check code after it
_marker = "# --- USER CODE START ---"
_marker_pos = _source_to_check.find(_marker)
if _marker_pos != -1:
    _source_to_check = _source_to_check[_marker_pos + len(_marker):]

try:
    _tree = _ast.parse(_source_to_check)
except SyntaxError:
    pass  # Let the actual execution catch syntax errors
else:
    for _node in _ast.walk(_tree):
        if isinstance(_node, _ast.Import):
            for _alias in _node.names:
                _top = _alias.name.split(".")[0]
                if _top in _BLOCKED:
                    print(f"BLOCKED IMPORT: '{{_alias.name}}' is not allowed in the sandbox.")
                    _sys.exit(1)
        elif isinstance(_node, _ast.ImportFrom):
            if _node.module:
                _top = _node.module.split(".")[0]
                if _top in _BLOCKED:
                    print(f"BLOCKED IMPORT: '{{_node.module}}' is not allowed in the sandbox.")
                    _sys.exit(1)

# Also block dangerous builtins
import builtins as _builtins
_original_import = _builtins.__import__

def _restricted_import(name, *args, **kwargs):
    _top = name.split(".")[0]
    if _top in _BLOCKED:
        raise ImportError(f"BLOCKED IMPORT: '{{name}}' is not allowed in the sandbox.")
    return _original_import(name, *args, **kwargs)

_builtins.__import__ = _restricted_import
'''


def execute_code(code: str, test_code: str, allow_threading: bool = False) -> Tuple[str, bool, int]:
    """
    Execute code + test_code in a sandboxed subprocess.

    Returns:
        (output: str, timed_out: bool, execution_time_ms: int)

    The output contains both stdout and stderr merged, exactly as a developer
    would see in their terminal.
    """
    # Build the blocked imports list, optionally allowing threading
    blocked = [b for b in BLOCKED_IMPORTS if not (b == "threading" and allow_threading)]

    # Build the full script: import checker + user code + test code
    import_checker = _build_import_checker(blocked)
    full_script = import_checker + "\n# --- USER CODE START ---\n" + code + "\n" + test_code

    tmp_path = None
    try:
        # Write to a temporary file
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', prefix='sandbox_',
            delete=False, dir=tempfile.gettempdir()
        ) as tmp:
            tmp.write(full_script)
            tmp_path = tmp.name

        # Run in subprocess with timeout
        start_time = time.time()
        try:
            result = subprocess.run(
                ["python3", tmp_path],
                capture_output=True,
                text=True,
                timeout=EXECUTION_TIMEOUT_SECONDS,
                env={
                    "PATH": os.environ.get("PATH", "/usr/bin:/usr/local/bin"),
                    "HOME": os.environ.get("HOME", "/tmp"),
                    "PYTHONDONTWRITEBYTECODE": "1",
                }
            )
            elapsed_ms = int((time.time() - start_time) * 1000)
            output = result.stdout + result.stderr
            return (output.strip(), False, elapsed_ms)

        except subprocess.TimeoutExpired:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return (
                f"TIMEOUT: Code execution exceeded {EXECUTION_TIMEOUT_SECONDS} second limit and was killed.",
                True,
                elapsed_ms
            )

    except Exception as e:
        return (f"SANDBOX ERROR: {str(e)}", False, 0)

    finally:
        # Always clean up temp files
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
