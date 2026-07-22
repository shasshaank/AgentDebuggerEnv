#!/usr/bin/env bash
# One-time setup for a fresh Linux GPU box (RunPod / Vast.ai / Lambda / etc).
# Run from the repo root, after cloning the repo and cd-ing into it.
#
#   git clone <your-repo-url> AgentDebuggerEnv && cd AgentDebuggerEnv
#   bash scripts/setup_gpu_box.sh
set -euo pipefail

echo "== GPU check =="
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
else
  echo "WARNING: nvidia-smi not found -- no GPU visible on this box." >&2
fi

echo "== Python venv =="
PYTHON="${PYTHON:-python3}"
"$PYTHON" -m venv .venv
./.venv/bin/pip install --upgrade pip

echo "== Installing agentdebugger[train] (torch, transformers, trl, peft, datasets, accelerate, wandb) =="
./.venv/bin/pip install -e '.[train,dev]'

echo "== Sanity check: CUDA visible to torch =="
./.venv/bin/python -c "import torch; print('cuda available:', torch.cuda.is_available()); print('device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"

echo "== Fast test suite (sandbox + reward + dataset checks; no GPU needed) =="
./.venv/bin/python -m pytest -q -m "not slow"

cat <<'EOF'

Setup done. Next steps:

  1. Authenticate W&B so training curves get logged (optional but strongly
     recommended -- see docs/CONTEXT.md for what gets logged):
       export WANDB_API_KEY=...
       export WANDB_PROJECT=agentdebugger        # optional, just for organizing runs

  2. (Optional) HF token, only needed if push_to_hub or a gated model is used:
       export HF_TOKEN=...

  3. Run the calibration run FIRST (see docs/CONTEXT.md "Quick reference"):
       ./.venv/bin/python -m agentdebugger.cli train \
           --reward-config R0 --split train --max-steps 20 --seed 42 \
           --output-dir ./ckpt/calibration

  4. Then the real matrix:
       ./scripts/run_matrix.sh
EOF
