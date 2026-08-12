@echo off
chcp 65001 >nul
title KIS Trading Bot Dashboard

set KEY=C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading\oracle_key
set SERVER=ubuntu@141.148.172.12
set OUTFILE=%~dp0dashboard_live.html

echo ========================================
echo  Loading bot data from Oracle server...
echo ========================================
echo.

echo [1/3] Connecting to server...
ssh -i "%KEY%" -o StrictHostKeyChecking=no -o ConnectTimeout=10 %SERVER% "cd ~/kis-auto-trading && source venv/bin/activate && python3 fetch_dashboard_data.py 2>/dev/null" > "%TEMP%\bot_data.json" 2>nul

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Cannot connect to server.
    pause
    exit /b 1
)

echo [2/3] Generating dashboard...
python "%~dp0generate_dashboard.py" "%TEMP%\bot_data.json" "%OUTFILE%"

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Dashboard generation failed.
    pause
    exit /b 1
)

echo [3/3] Opening in browser...
start "" "%OUTFILE%"

echo.
echo Done! Dashboard opened in browser.
timeout /t 3 >nul
