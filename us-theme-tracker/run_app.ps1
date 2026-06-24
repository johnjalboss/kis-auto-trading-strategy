# run_app.ps1
# Script to run the US Stock Fine-Grained Theme Tracker App

Write-Host "=============================================" -ForegroundColor Green
Write-Host "  US Stock Fine-Grained Theme Tracker Launcher" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""

# Ensure we are in the correct directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# 1. Check if port 8501 is already active
$portActive = Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue
if ($portActive) {
    Write-Host "Streamlit server is already running. Opening browser..." -ForegroundColor Green
    Start-Process "http://localhost:8501"
    Exit 0
}

# 2. Check if streamlit is installed
$streamlitCheck = python -c "import streamlit" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing python dependencies from requirements.txt..." -ForegroundColor Yellow
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install dependencies. Please run 'pip install -r requirements.txt' manually." -ForegroundColor Red
        Exit 1
    }
}

Write-Host "Launching Streamlit Dashboard..." -ForegroundColor Cyan

# Force-open default browser after 2 seconds to ensure the page loads
Start-Job -ScriptBlock { 
    Start-Sleep -Seconds 2
    Start-Process "http://localhost:8501" 
} | Out-Null

python -m streamlit run app.py --server.port 8501 --server.headless true

