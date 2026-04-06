"""
AgentDebuggerEnv — FastAPI Server
===================================
Exposes the environment as REST endpoints:
  POST /reset  — Start a fresh episode
  POST /step   — Submit one action
  GET  /state  — Full internal state
  GET  /health — Deployment health check (must return 200)
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from env.environment import DebuggerEnvironment
from env.models import Action
from env.tasks.registry import list_tasks

app = FastAPI(
    title="AgentDebuggerEnv",
    description="An OpenEnv-compliant debugging environment for AI agents",
    version="1.0.0",
)

# Single environment instance (single-session design as per hackathon constraints)
env = DebuggerEnvironment()


class ResetRequest(BaseModel):
    task_id: str


@app.get("/health")
async def health():
    """Health check — must return HTTP 200 always. Critical for hackathon Phase 1."""
    return {"status": "ok", "environment": "agentdebugger-env", "version": "1.0.0"}


@app.post("/reset")
async def reset(request: ResetRequest):
    """Start a fresh episode. Returns initial Observation."""
    try:
        observation = env.reset(request.task_id)
        return JSONResponse(content=observation, status_code=200)
    except ValueError as e:
        return JSONResponse(
            content={"error": str(e), "available_tasks": list_tasks()},
            status_code=400,
        )
    except Exception as e:
        return JSONResponse(
            content={"error": f"Internal error during reset: {str(e)}"},
            status_code=200,
        )


@app.post("/step")
async def step(action: Action):
    """Submit one action. Returns {observation, reward, done, info}. Always HTTP 200."""
    try:
        result = env.step(action)
        return JSONResponse(content=result, status_code=200)
    except Exception as e:
        # Never return 500 — all errors go in response body
        return JSONResponse(
            content={
                "observation": {},
                "reward": {
                    "step_reward": 0.0,
                    "cumulative_reward": 0.0,
                    "grader_score": 0.0,
                    "breakdown": {},
                },
                "done": False,
                "info": {"error": f"Internal error: {str(e)}"},
            },
            status_code=200,
        )


@app.get("/state")
async def get_state():
    """Return full internal environment state as a plain dict."""
    try:
        state = env.state()
        return JSONResponse(content=state, status_code=200)
    except Exception as e:
        return JSONResponse(
            content={"error": f"Internal error: {str(e)}"},
            status_code=200,
        )
