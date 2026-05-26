@echo off
title AI Swing Trading Bot - One-Click Launcher
chcp 65001 >nul
color 0A

echo ===================================================================
echo 🤖 AI 스윙 트레이딩 봇 - 원클릭 구동기 (One-Click Launcher)
echo ===================================================================
echo.

:: 1. 파이썬 설치 여부 검사
echo [1 단계] 파이썬(Python) 환경을 확인하는 중...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo ❌ 에러: 컴퓨터에 파이썬(Python)이 설치되어 있지 않거나 PATH 등록이 누락되었습니다!
    echo.
    echo 해결 방법:
    echo 1. https://www.python.org/downloads/ 에서 최신 Python 3.x 버전을 다운로드하여 설치하십시오.
    echo 2. 설치 시 반드시 "Add Python to PATH" 체크박스에 체크해 주십시오.
    echo.
    echo 🌐 웹 브라우저로 파이썬 공식 다운로드 페이지를 띄워 드립니다...
    start https://www.python.org/downloads/
    echo.
    pause
    exit /b
)
echo.

:: 2. 필수 라이브러리 자동 설치
echo [2 단계] 필수 패키지 라이브러리를 동기화 및 설치하는 중...
echo (처음 한 번만 시간이 다소 소요될 수 있으며, 이후부터는 즉시 스킵됩니다.)
echo.
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo ⚠️ 경고: 일부 라이브러리 패키지 설치에 실패했습니다. 인터넷 연결을 확인해 주십시오.
)
:: 2.5. 전략 자동 업데이트 동기화
echo [2.5 단계] 원격 저장소에서 최신 전략 패치를 자동 검사 및 동기화하는 중...
python updater.py
echo.

:: 3. .env 설정파일 존재 여부 확인
echo [3 단계] 개인 설정 정보를 확인하는 중...
if not exist ".env" (
    echo.
    echo ℹ️ 알림: 개인 설정(.env)이 발견되지 않았습니다.
    echo      초기 연동을 위한 설정 마법사 GUI 창을 가동합니다...
    echo.
    python setup_wizard.py
    exit /b
)

:: 4. .env 파일이 이미 존재할 경우: 메뉴 선택 제공
cls
echo ===================================================================
echo 🤖 AI 스윙 트레이딩 봇 - 제어 센터 (Control Center)
echo ===================================================================
echo.
echo [1] 🚀 AI 자동 매매 시작 (로컬 구동)
echo [2] ⚙️ 설정 마법사 열기 (API 키 수정 / 클라우드 서버 배포)
echo [3] ❌ 종료
echo.
set /p opt="원하시는 작업 번호를 입력하고 Enter를 누르세요 [1/2/3]: "

if "%opt%"=="1" (
    cls
    echo ===================================================================
    echo 🚀 AI 자동 매매 구동 시작! (이 창을 닫으면 매매가 중지됩니다)
    echo ===================================================================
    echo.
    python main.py
) else if "%opt%"=="2" (
    echo.
    echo ⚙️ 설정 마법사를 실행하는 중...
    python setup_wizard.py
) else (
    echo.
    echo 👋 프로그램을 종료합니다. 감사합니다!
    timeout /t 2 >nul
)
