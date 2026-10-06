@echo off
title ArtifactX Frontend [Vite:5173]
set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%\frontend"

echo ==========================================
echo    ArtifactX UI Frontend (Port 5173)      
echo ==========================================
echo Starting Vite dev server...
echo.

npm run dev

pause
