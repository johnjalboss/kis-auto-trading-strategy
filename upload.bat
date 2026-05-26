@echo off
title AI Swing Bot - One-Click GitHub Uploader
chcp 65001 >nul
color 0B

echo ===================================================================
echo 🚀 AI 스윙 트레이딩 봇 - 원클릭 깃허브 업로더 (One-Click Uploader)
echo ===================================================================
echo.

:: 1. version.json 자동 패치 버프 (Python 원라이너로 version.json의 패치 버전 카운트업)
echo [1 단계] version.json 전략 버전을 한 단계 올리는 중...
python -c "import json; f=open('version.json','r',encoding='utf-8'); d=json.load(f); v=d['version'].split('.'); v[-1]=str(int(v[-1])+1); d['version']='.'.join(v); f.close(); f=open('version.json','w',encoding='utf-8'); json.dump(d,f,indent=2); f.close(); print('수정 완료: v' + d['version'])"
echo.

:: 2. Git 명령어 대행 실행
echo [2 단계] 최신 전략 코드를 깃허브 저장소에 쏘아 올리는 중...
"C:\Program Files\Git\cmd\git.exe" add .
"C:\Program Files\Git\cmd\git.exe" commit -m "Auto-update: Manual strategies patch"
"C:\Program Files\Git\cmd\git.exe" push origin main

if %errorlevel% neq 0 (
    color 0C
    echo.
    echo ❌ 에러: 깃허브 업로드(Push)에 실패했습니다!
    echo       처음 푸시하는 경우 로그인/브라우저 인증이 필요할 수 있습니다.
    echo.
    pause
    exit /b
)

echo.
echo ===================================================================
echo 🎉 원격 깃허브 저장소(johnjalboss)로 배포 완벽 성공!
echo   이제 모든 친구들의 매매 봇이 자동으로 최신 버전으로 업데이트됩니다!
echo ===================================================================
echo.
pause
