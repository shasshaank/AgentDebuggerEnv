---
title: AgentDebugger-Env 🐛
emoji: 📈
colorFrom: yellow
colorTo: green
sdk: docker
app_port: 8000
pinned: true
license: mit
---

# AgentDebuggerEnv 🐛

> **Benchmarking Agentic Reasoning through the Iterative Hypothesis-Test-Fix Loop.**

**AgentDebuggerEnv** is an OpenEnv-compliant benchmarking environment designed for the **Meta + PyTorch + HuggingFace OpenEnv Hackathon**. Unlike static code-repair benchmarks that only measure the final output, AgentDebuggerEnv evaluates the *cognitive trajectory* of an agent: how it forms hypotheses, interprets execution failures, and iterates toward a solution in a secure, live sandbox.

---

## 📊 Baseline Performance

Tested with **GPT-4o** using the standard `inference.py` script:

- **Easy (0.85)**: Solved in 1-2 attempts; clear signal from error output.
- **Medium (0.50)**: Solved in ~4 attempts; agents must resist a red-herring authentication error.
- **Hard (0.18)**: Rarely solved; agents must proactively design concurrent tests to surface the hidden race condition.
- **Mean Score: 0.51**

*Measurements taken over multiple runs to account for LLM variance. See `openenv.yaml` for full metadata.*

---

## 🚀 The Core Philosophy

Traditional benchmarks (like HumanEval or MBPP) are "one-shot": the model sees a prompt and writes code. Real-world engineering is **iterative**.

AgentDebuggerEnv forces agents to operate in a **live feedback loop**:
1.  **Observe**: Analyze existing buggy code and initial test failures.
2.  **Hypothesize**: Explicitly state a theory about the root cause (scored for accuracy).
3.  **Act**: Submit a surgical fix or query the environment for more context.
4.  **Verify**: Observe real-time `stdout/stderr` from a sandboxed test suite execution.

---

## 🛠️ Technical Architecture

### 1. Robust Security Sandbox
Every submission is executed in a multi-layered isolated environment:
*   **AST Filtering**: A deep Abstract Syntax Tree (AST) pass analyzes submitted code before execution, blocking dangerous imports (`os`, `sys`, `subprocess`, `socket`, etc.) and preventing the override of security-critical builtins.
*   **Process Isolation**: Executes in a separate subprocess with strict resource limits (CPU/Memory) enforced via container runtime and execution timeouts (15s). Any attempt to hang the environment results in immediate termination.
*   **Thread Safety**: A specialized "Concurrency Sandbox" allows multi-threaded tests (essential for the Hard Task) while maintaining strict host-level security boundaries.

### 2. High-Fidelity Feedback
Instead of binary `Pass/Fail` bits, the environment returns the **raw execution stream**. This allows agents to:
*   Read stack traces.
*   See partial progress (e.g., "6 passed, 2 failed").
*   Detect timeouts and resource exhaustion.

---

## 📁 Task Suite & Reasoning Challenges

| Task | Difficulty | Reasoning Challenge | Why it's hard |
| :--- | :--- | :--- | :--- |
| **Easy** | 🟢 Easy | **Off-by-One** | Requires basic logic verification. The error message is high-signal. |
| **Medium** | 🟡 Medium | **Red Herring** | The symptom (MD5 hashing error) manifests far from the root cause. Agent must trace data flow backward. |
| **Hard** | 🔴 Hard | **Race Condition** | **Invisible to sequential tests.** The agent must reason that passing tests do *not* mean the code is correct, and design a concurrent stress test. |

---

## 📊 Professional Grading Methodology

Our graders don't just check if the code works at the end. They score the **process**:

*   **Sequential Correctness (40%)**: Does the fix pass the original unit tests?
*   **Hidden Strength (30%)**: Does the fix survive a high-concurrency (1000-thread) stress test? (Hard task only).
*   **Hypothesis Accuracy (20%)**: Did the agent correctly identify the bug? (NLP-based keyword matching against ground truth).
*   **Efficiency Bonus (10%)**: Did the agent solve it within 5 attempts?

---

## ⚙️ Installation & Usage

### 📦 Local Setup
```bash
git clone https://huggingface.co/spaces/shashaank0707/AgentDebugger-env
cd AgentDebugger-env
pip install -e .
```

### 🚢 Running the Environment
```bash
# Start the FastAPI server
uvicorn env.server:app --host 0.0.0.0 --port 8000
```

### 🤖 Running an Agent (OpenEnv Baseline)
```bash
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o"
export HF_TOKEN="your_openai_key"
export ENV_BASE_URL="http://localhost:8000"
python inference.py
```

---

### 🔐 Environment Variables

| Variable | Description | Standard Fallback |
| :--- | :--- | :--- |
| `API_BASE_URL` | LLM API endpoint | `https://api.openai.com/v1` |
| `MODEL_NAME` | Model to evaluate | `gpt-4o` |
| `HF_TOKEN` | Auth token (or OpenAI key) | — |
| `OPENAI_API_KEY` | Alternative auth token | — |
| `ENV_BASE_URL` | Address of the FastAPI server | `http://localhost:8000` |

---

## 🔗 OpenEnv API Compliance

AgentDebuggerEnv implements the full OpenEnv specification:

*   `POST /reset`: Initialize a task (`{"task_id": "medium"}`).
*   `POST /step`: Submit an `Action` (supports `submit_fix`, `query_context`, `give_up`).
*   `GET /state`: Retrieve full episode history and current environment state.
*   `GET /health`: Standard health check for automated uptime monitoring.

---

## 📜 Metadata & License
*   **License**: [MIT](LICENSE)
*   **Author**: Shashaank (GitHub: @shasshaank, HF: @shashaank0707)
*   **Hackathon**: Meta + PyTorch + HuggingFace OpenEnv 2024

---

### ✅ Submission Integrity
- **Commit SHA**: `159a5faf82fc1ab3709f9674becf9a3ec55cf562`
- **Last Verified Sync**: 2026-04-08
- **Platform Match**: GitHub and HF Space are identical at this HEAD.
