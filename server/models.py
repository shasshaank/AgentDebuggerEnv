"""
server/models.py — Re-exports structured agent types for training scripts.
All core types live in env/models.py; this module exposes them under the
`server` namespace so training/train_grpo.py can import without path changes.
"""

from env.models import (  # noqa: F401
    StructuredAgentOutput,
    parse_agent_output,
    VALID_ACTIONS,
)
