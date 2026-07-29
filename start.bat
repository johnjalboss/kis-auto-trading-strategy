@echo off
title AI Swing Trading Bot - One-Click Launcher
chcp 65001 >nul

echo ===================================================================
echo AI Swing Trading Bot - One-Click Launcher
echo ===================================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH!
    echo Download and install Python 3.x from https://www.python.org/downloads/
    pause
    exit /b
)

echo [1/3] Checking dependencies...
python -m pip install -r requirements.txt

echo.
echo [2/3] Checking remote updates...
python updater.py

echo.
echo [3/3] Starting Bot...
if not exist ".env" (
    echo [.env file missing] Launching GUI Setup Wizard...
    python setup_wizard.py
) else (
    python main.py
)

pause
