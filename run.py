"""ArtifactX Backend Runner.

Can be run directly via:
    python run.py
or
    .venv\\Scripts\\python run.py

Automatically sets up PYTHONPATH and starts Uvicorn on http://127.0.0.1:8080.
"""

import os
import sys
from pathlib import Path

# Always guarantee root is in sys.path and env
ROOT_DIR = Path(__file__).resolve().parent
if ROOT_DIR.name == "backend":
    ROOT_DIR = ROOT_DIR.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ["PYTHONPATH"] = str(ROOT_DIR)

if __name__ == "__main__":
    import uvicorn
    print("\n==========================================")
    print("   ArtifactX Forensic Engine (Backend)   ")
    print("==========================================")
    print("API Server  : http://127.0.0.1:8080")
    print("API Docs    : http://127.0.0.1:8080/docs")
    print("Health Check: http://127.0.0.1:8080/api/health")
    print("==========================================\n")
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8080, reload=True)
