# ArtifactX Development Server Launcher
$ErrorActionPreference = "Stop"
$rootDir = $PSScriptRoot

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "       Starting ArtifactX Platform        " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Set PYTHONPATH to project root for module imports
$env:PYTHONPATH = $rootDir

# Check Python virtual environment
$pythonExe = Join-Path $rootDir ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Host "[!] Virtual environment not found at .venv. Run setup first." -ForegroundColor Red
    exit 1
}

Write-Host "[1/2] Starting FastAPI backend on http://127.0.0.1:8080..." -ForegroundColor Green
$backendProcess = Start-Process -FilePath $pythonExe -ArgumentList "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8080", "--reload" -WorkingDirectory $rootDir -PassThru

Start-Sleep -Seconds 2

Write-Host "[2/2] Starting Vite frontend on http://localhost:5173..." -ForegroundColor Green
$frontendDir = Join-Path $rootDir "frontend"
$frontendProcess = Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" -WorkingDirectory $frontendDir -PassThru

Write-Host ""
Write-Host "ArtifactX is running!" -ForegroundColor Cyan
Write-Host "  Frontend : http://localhost:5173" -ForegroundColor Yellow
Write-Host "  Backend  : http://127.0.0.1:8080" -ForegroundColor Yellow
Write-Host "  API Docs : http://127.0.0.1:8080/docs" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Ctrl+C to terminate or close this window." -ForegroundColor Gray

try {
    Wait-Process -Id $backendProcess.Id, $frontendProcess.Id
} finally {
    if ($backendProcess -and -not $backendProcess.HasExited) { Stop-Process -Id $backendProcess.Id -Force }
    if ($frontendProcess -and -not $frontendProcess.HasExited) { Stop-Process -Id $frontendProcess.Id -Force }
}
