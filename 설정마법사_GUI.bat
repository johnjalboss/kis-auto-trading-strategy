@echo off
title AI Swing Trading Bot - GUI Setup Wizard
chcp 65001 >nul

echo ===================================================================
echo AI Swing Trading Bot - GUI Setup Wizard
echo ===================================================================
echo.
echo Starting GUI Setup Wizard...
echo.

python -m pip install -r requirements.txt >nul 2>&1
python setup_wizard.py

pause
