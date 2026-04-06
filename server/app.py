"""
Server Entry Point for AgentDebuggerEnv
========================================
Main entry point to start the FastAPI server for the AgentDebugger environment.
"""

import uvicorn
from env.server import app

def main():
    """Main execution function to run the FastAPI server."""
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=1)

if __name__ == "__main__":
    main()
