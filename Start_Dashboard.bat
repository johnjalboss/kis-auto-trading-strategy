@echo off
echo ===================================================
echo KIS AUTO-TRADING BOT - DASHBOARD LAUNCHER
echo ===================================================
echo.
echo Checking for required libraries (streamlit, plotly)...
python -m pip install streamlit plotly pandas --quiet --disable-pip-version-check --no-warn-script-location 2>nul

echo.
echo Launching the Real-Time Web Dashboard...
for /f "delims=" %%i in ('python -c "import site; print(site.getuserbase() + '\\Scripts\\streamlit.exe')"') do set STREAMLIT_EXE=%%i

if exist "%STREAMLIT_EXE%" (
    "%STREAMLIT_EXE%" run dashboard_app.py
) else (
    echo [ERROR] Streamlit not found at %STREAMLIT_EXE%. Trying base command...
    python -m streamlit run dashboard_app.py
)

pause
