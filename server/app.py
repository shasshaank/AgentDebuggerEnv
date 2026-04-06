"""
Server Entry Point for AgentDebuggerEnv
========================================
This file satisfies the OpenEnv validator requirement for 'server/app.py'.
It imports the FastAPI app from 'env.server' and provides a main() function.
"""

import uvicorn
from env.server import app

def main():
    """Main function called by the 'server' script defined in pyproject.toml."""
    # Runs the server on port 8000 as required by the hackathon spec
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=1)

if __name__ == "__main__":
    main()
