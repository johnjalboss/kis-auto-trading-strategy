# 🚀 AI 퀀트 스윙 트레이딩 봇 v2.0 (미국 주식 자동매매)

월가 헤지펀드 스타일의 퀀트 알파 알고리즘(130+ 개 모듈) 기반 미국 주식 무인 자동매매 프로그램입니다.

---

## 📌 주요 특징
1. **기관 퀀트 알파 샤프 모멘텀 수식 (Vol-Adj Sharpe Momentum)**: 변동성이 적고 매끄럽게 우상향하는 1등 주도주를 선제 포착합니다.
2. **약세장/순환매 자동 판별 엔진**: 기술주 조정 시 경기방어 1등주(Healthcare, Consumer Staples 등)로 자금을 자동 순환 배치합니다.
3. **고점 추적 트레일링 스탑 & ATR 분할 익절**: 번 수익을 1달러도 안 뺏기고 밀착 보호합니다.
4. **무인 원격 자동 업데이트 시스템**: 프로그램 실행 시 최신 전략 알고리즘을 깃허브 서버에서 자동으로 패치 받습니다.

---

## 🛠️ 3분 환경 설정 및 시작 가이드

### 1단계: 파이썬 및 필수 패키지 설치
* 파이썬 3.10 이상이 설치되어 있어야 합니다. (설치 시 `Add Python to PATH` 옵션 반드시 체크!)
* 명령 프롬프트(CMD) 또는 터미널에서 다음 명령어를 실행합니다:
  ```bash
  pip install -r requirements.txt
  ```

### 2단계: 본인 계좌 API Key 설정
1. 폴더 안의 `.env.example` 파일 이름을 `.env` 로 변경합니다.
2. `.env` 파일을 메모장 등으로 열어 본인의 증권사 API Key 및 텔레그램 알림 키를 입력합니다:
   ```ini
   # ----------------------------------------------------
   # 한국투자증권 해외주식 API (필수)
   # ----------------------------------------------------
   KIS_APP_KEY=본인의_한국투자증권_AppKey
   KIS_APP_SECRET=본인의_한국투자증권_AppSecret
   CANO=본인_계좌번호_8자리
   ACNT_PRDT_CD=01
   IS_VIRTUAL=False

   # ----------------------------------------------------
   # 텔레그램 실시간 알림 (선택 사항 - 권장)
   # ----------------------------------------------------
   TELEGRAM_BOT_TOKEN=본인의_텔레그램_봇토큰
   TELEGRAM_CHAT_ID=본인의_텔레그램_채팅ID

   # ----------------------------------------------------
   # Google Gemini AI API (선택 사항)
   # ----------------------------------------------------
   GEMINI_API_KEY=본인의_Gemini_API_Key
   ```

---

## 🖥️ 실행 방법

### 방법 A (내 PC 윈도우):
폴더 안의 **`start.bat`** 파일을 더블클릭합니다.

### 방법 B (내 PC 터미널):
```bash
python main.py
```

---

## ☁️ 오라클 클라우드 (Oracle VPS) 24시간 무중단 구동 가이드

컴퓨터를 꺼두어도 클라우드에서 24시간 자동매매가 실행되도록 오라클 무료 서버를 사용하는 법입니다.

1. **오라클 클라우드 가입 및 Ubuntu 22.04 인스턴스 생성**
2. **SSH 접속 및 환경 구축**:
   ```bash
   ssh -i your_ssh_key.key ubuntu@<YOUR_VPS_IP>
   sudo apt update && sudo apt install -y python3-pip python3-venv git
   ```
3. **가상환경 및 라이브러리 설치**:
   ```bash
   python3 -m venv venv
   ./venv/bin/pip install -r requirements.txt
   ```
4. **24시간 자동 재가동 크론탭(Crontab) 등록**:
   ```bash
   crontab -e
   # 아랫줄에 추가:
   * * * * * pgrep -f main.py > /dev/null || /home/ubuntu/kis-auto-trading/venv/bin/python /home/ubuntu/kis-auto-trading/main.py >> /home/ubuntu/kis-auto-trading/logs/cron.log 2>&1
   ```

---

## ❓ 자주 묻는 질문 (FAQ)
* **Q: 자동으로 프로그램 업데이트가 되나요?**  
  A: 네! `main.py` 실행 시 무인 원격 자동 업데이트 엔진(`updater.py`)이 깃허브 최신 전략을 감지하여 덮어쓰기 패치합니다.
* **Q: 모의투자로 테스트해 볼 수 있나요?**  
  A: `python main.py --dry-run` 명령어로 실행하시면 실제 주문을 넣지 않고 모의 시뮬레이션 매매를 진행할 수 있습니다.
