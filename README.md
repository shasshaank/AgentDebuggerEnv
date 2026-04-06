---
title: AgentDebugger Env 🐛
emoji: 📈
colorFrom: yellow
colorTo: green
sdk: docker
app_port: 8000
pinned: false
---

# AgentDebuggerEnv 🐛

> **Benchmarking Agentic Reasoning through the Iterative Hypothesis-Test-Fix Loop.**

An OpenEnv-compliant environment designed for the **Meta + PyTorch + HuggingFace OpenEnv Hackathon**. Unlike static code-repair benchmarks, **AgentDebuggerEnv** focuses on the *trajectory* of an agent's reasoning—measuring how effectively an agent forms hypotheses, observes failures, and iterates toward a solution in a live execution sandbox.

---

## 🚀 Overview

Debugging is one of the highest-leverage cognitive tasks in software engineering. Modern LLM agents often struggle with:
-   **Red Herrings**: Following misleading error messages to the wrong function.
-   **Stagnant Iteration**: Repeating the same failed fix attempt instead of updating their hypothesis based on new output.
-   **Concurrency Failures**: Failing to detect or fix non-deterministic bugs (race conditions).

**AgentDebuggerEnv** makes these failures measurable and scorable. The environment provides a live, sandboxed feedback loop where agents submit complete code fixes and receive real-time execution results.

---

## 🛠️ Core Mechanics: The Feedback Loop

The environment follows the standard OpenEnv interface (`reset`, `step`, `state`) but enforces a strict **Hypothesis-Test-Fix** cycle:

1.  **Hypothesis**: The agent must state its theory about the bug before every fix attempt. 
2.  **Execution**: The submitted code is executed in a secure sandbox with hard timeouts.
3.  **Observation**: The agent receives the actual `stdout` + `stderr` from the test suite, not just a binary pass/fail.
4.  **Reward**: Dense reward signal is provided at every step, scaling with test progress and hypothesis accuracy.

---

## 📁 Tasks & Difficulty

The environment includes three standardized tasks designed to test different facets of agentic reasoning:

| Task | Difficulty | Core Challenge |
| :--- | :--- | :--- |
| **Easy** | Easy | **Off-by-One**: Simple logic bug with an explicit, high-signal error message. |
| **Medium** | Medium | **Red Herring**: Interdependent functions where the error manifests far from the root cause. |
| **Hard** | Hard | **Race Condition**: A concurrency bug that is invisible to sequential tests. Agent must design a concurrent test to surface it. |

---

## ⚙️ How It Works (Spec Compliance)

### Data Models
- **Observation**: Includes `buggy_code`, `test_suite`, `previous_attempts` (full history), and `current_error_output`.
- **Action**: Supports `submit_fix` (requires `hypothesis`), `query_context` (for deeper code analysis), and `give_up`.
- **Reward**: A multi-component reward including `test_progress`, `hypothesis_match`, and `efficiency_bonus`.

### Infrastructure
-   **FastAPI**: Exposes standard endpoints on port 8000.
-   **Docker**: Fully containerized and ready for HuggingFace Spaces.
-   **Security**: Robust AST-based filtering to prevent malicious code escape.
-   **Baseline Script**: Includes a reference `inference.py` script that uses the OpenAI client for benchmark evaluation.

---

## 📦 Quick Start

### Installation
```bash
git clone https://huggingface.co/spaces/shashaank/agentdebugger-env
cd agentdebugger-env
pip install -r requirements.txt
```

### Running Locally
```bash
# Start the environment server
uvicorn env.server:app --host 0.0.0.0 --port 8000

# Run the baseline inference (requires API key)
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o"
export HF_TOKEN="your_key_here"
python inference.py
```

---

## 📊 Benchmarking Results (GPT-4o Baseline)

| Task | Grader Score | Solved |
| :--- | :--- | :--- |
| Easy | 0.85 | Yes |
| Medium | 0.50 | Mixed |
| Hard | 0.18 | No |

---

## 📜 License
MIT License. Created by **shashaank** for the Meta / PyTorch / HuggingFace OpenEnv Hackathon.
