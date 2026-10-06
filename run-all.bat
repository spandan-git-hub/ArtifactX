@echo off
title ArtifactX Launcher
set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

echo ==========================================
echo       Starting ArtifactX Platform         
echo ==========================================
echo [1/2] Launching Backend on http://127.0.0.1:8080...
start "ArtifactX Backend" cmd /k ""%PROJECT_ROOT%run-backend.bat""

timeout /t 2 /nobreak >nul

echo [2/2] Launching Frontend on http://localhost:5173...
start "ArtifactX Frontend" cmd /k ""%PROJECT_ROOT%run-frontend.bat""

echo.
echo ==========================================
echo Both services launched in separate windows!
echo - Frontend UI : http://localhost:5173
echo - Backend API : http://127.0.0.1:8080
echo - Swagger Docs: http://127.0.0.1:8080/docs
echo ==========================================
