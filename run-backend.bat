@echo off
title ArtifactX Backend [FastAPI:8080]
set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

set "PYTHONPATH=%PROJECT_ROOT%"

if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" (
    "%PROJECT_ROOT%\.venv\Scripts\python.exe" "%PROJECT_ROOT%\run.py"
) else (
    echo [ERROR] Virtual environment not found at %PROJECT_ROOT%\.venv
    python "%PROJECT_ROOT%\run.py"
)

pause
