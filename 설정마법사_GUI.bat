@echo off
title AI Swing Trading Bot - GUI Setup Wizard
chcp 65001 >nul
color 0B

echo ===================================================================
echo 🕊️ AI 스윙 트레이딩 봇 - 원클릭 GUI 설정 마법사
echo ===================================================================
echo.
echo GUI 설정 화면을 실행하는 중입니다...
echo.

python -m pip install -r requirements.txt >nul 2>&1
python setup_wizard.py

pause
