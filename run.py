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

# Self-bootstrap: if invoked with system Python instead of .venv, re-execute inside workspace .venv
_venv_python = ROOT_DIR / ".venv" / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
if _venv_python.exists():
    try:
        _current_exe = Path(sys.executable).resolve()
        _target_exe = _venv_python.resolve()
        if _current_exe != _target_exe:
            import subprocess
            sys.exit(subprocess.call([str(_target_exe), *sys.argv]))
    except Exception:
        pass

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ["PYTHONPATH"] = str(ROOT_DIR)

if __name__ == "__main__":
    if "--check" in sys.argv:
        from backend.app.main import app
        print("Backend check OK")
        sys.exit(0)

    import uvicorn
    print("\n==========================================")
    print("   ArtifactX Forensic Engine (Backend)   ")
    print("==========================================")
    print("API Server  : http://127.0.0.1:8080")
    print("API Docs    : http://127.0.0.1:8080/docs")
    print("Health Check: http://127.0.0.1:8080/api/health")
    print("==========================================\n")
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8080, reload=True)
