"""ArtifactX Backend Runner (backend folder shortcut)."""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

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
    print("==========================================\n")
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8080, reload=True)
