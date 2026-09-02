# 🚀 KIS 미국주식 SOTA 퀀트 자동매매 시스템 완벽 사용설명서
> **초보자도 3분 만에 마스터하는 24시간 완전 무인 인공지능 자산 증식 가이드**

---

## 📑 목차 (Table of Contents)
1. [🌟 시스템 소개 및 핵심 특징](#1-시스템-소개-및-핵심-특징)
2. [⚡ 3분 퀵 스타트 가이드 (처음 시작하기)](#2-3분-퀵-스타트-가이드-처음-시작하기)
3. [📱 텔레그램 원클릭 스마트 리모컨 완벽 해설 (32개 메뉴)](#3-텔레그램-원클릭-스마트-리모컨-완벽-해설)
4. [🚨 비상 제어 및 6중 리스크 안전망](#4-비상-제어-및-6중-리스크-안전망)
5. [🧠 5대 직교 퀀트 알파 & 12대 매크로 엔진 원리](#5-5대-직교-퀀트-알파--12대-매크로-엔진-원리)
6. [💎 실전 퀀트 투자 운용 수칙 & 십계명](#6-실전-퀀트-투자-운용-수칙--십계명)
7. [🛠️ 자주 묻는 질문(FAQ) & 문제 해결](#7-자주-묻는-질문faq--문제-해결)

---

## 1. 🌟 시스템 소개 및 핵심 특징

본 시스템은 **한국투자증권(KIS) 공식 OpenAPI**와 **미국 세인트루이스 연준(FRED), SEC 공시(13F/Form 4), CBOE 옵션, 다크풀(ATS)** 데이터를 실시간 융합하여 미국 주식 3,002개 전 종목 중 **가장 확실한 1등 주도주만 선별 자동 매매**하는 인공지능 퀀트 트레이딩 머신입니다.

### ✨ 핵심 특장점
* **24시간 완전 자율 무인 매매**: 종목 스캔 ➔ 5대 팩터 채점 ➔ 켈리 베팅 비중 계산 ➔ 분할 매수/익절/손절 100% 자동 집행.
* **스마트폰 텔레그램 원클릭 제어**: PC 없이도 스마트폰 버튼 하나로 계좌 잔고, 수익률, 추천 종목, 매크로 D-Day 확인 및 긴급 청산 가능.
* **월가 헤지펀드급 5대 직교 팩터**: 칼만 필터 제로랙 속도 + OFI 오더플로우 매집 + PEAD 어닝 서프라이즈 + 13F 다크풀 매집 + 거시경제.
* **철저한 원금 보존 6중 안전장치**: 단일 종목 손절(-3.8%), 주간 손실 한도(-15%), 계좌 MDD(-25%), 14일 뇌동매매 방지 격리망.

---

## 2. ⚡ 3분 퀵 스타트 가이드 (처음 시작하기)

### Step 1. 증권사 및 텔레그램 API 키 준비
1. **한국투자증권 (KIS Developers)**:
   * [KIS Developers 사이트](https://apiportal.koreainvestment.com) 접속 ➔ KIS OpenAPI 서비스 신청 (모의/실전).
   * `App Key`, `App Secret`, `종합계좌번호 (8자리-01)` 발급.
2. **텔레그램 봇 토큰 발급**:
   * 텔레그램 앱에서 `@BotFather` 검색 ➔ `/newbot` 입력하여 봇 생성 및 `Bot Token` 복사.
   * `@userinfobot` 검색 후 대화를 걸어 본인의 `Chat ID (숫자)` 확인.

### Step 2. 환경 설정 파일 (`.env`) 작성
프로젝트 폴더 내의 `.env` 파일에 발급받은 키를 입력합니다:
```env
# 한국투자증권 실전 계좌 정보
KIS_APP_KEY=your_kis_app_key_here
KIS_APP_SECRET=your_kis_app_secret_here
KIS_ACCOUNT_NO=12345678-01
KIS_IS_PAPER=false

# 텔레그램 봇 연동
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ
TELEGRAM_CHAT_ID=123456789

# 외부 퀀트 데이터 API (선택/권장)
FINNHUB_API_KEY=your_finnhub_api_key_here
```

### Step 3. 프로그램 실행
* **로컬 PC (Windows/Mac)**:
  ```bash
  # 백그라운드 통합 실행
  python orchestrator.py
  ```
* **오라클 클라우드 VPS (Linux 상시 무중단)**:
  ```bash
  # 텔레그램 대화형 봇 데몬 실행
  nohup python -u telegram_interactive_bot.py > bot.log 2>&1 &
  ```

---

## 3. 📱 텔레그램 원클릭 스마트 리모컨 완벽 해설

텔레그램 채팅창에 `/start` 또는 `메뉴`를 입력하면 아래와 같은 **스마트 제어판 버튼**이 나타납니다. 각 버튼을 누르면 실시간 데이터와 전문가 조언이 0.5초 만에 도착합니다.

```
┌────────────────────────────────────────────────────────┐
│ 📊 봇 상태 요약    │ 📈 보유 포지션 브리핑 │ 💰 오늘 실현손익 │
├────────────────────┼─────────────────────┼────────────────────┤
│ 📅 7일 주간 성과   │ 📅 30일 월간 성과    │ 🏆 전체 누적 성과  │
├────────────────────┼─────────────────────┼────────────────────┤
│ 🚀 실시간 후보 Top5│ 👑 주도 테마 1등주  │ 🎯 스크리너 픽     │
├────────────────────┼─────────────────────┼────────────────────┤
│ 🌐 시장 레짐 분석  │ 🛡️ 리스크 현황      │ 🎲 몬테카를로 파산 │
├────────────────────┼─────────────────────┼────────────────────┤
│ 🕶️ 다크풀 장외매집 │ 📊 CBOE 풋/콜&SKEW  │ 🧲 GEX 감마 레이더 │
├────────────────────┼─────────────────────┼────────────────────┤
│ 🏛️ 의원 주식 매매  │ 📰 AI 뉴스 감성     │ 📡 스마트머니 수급 │
├────────────────────┼─────────────────────┼────────────────────┤
│ 🔄 테마 순환매     │ 🏛️ 연준 순유동성    │ 👥 내부자 순매수   │
├────────────────────┼─────────────────────┼────────────────────┤
│ ⏰ 거시 지표 쉴드  │ 🔮 매크로 D-Day     │ 🏛️ 경제 서프라이즈 │
├────────────────────┼─────────────────────┼────────────────────┤
│ ⚙️ 파라미터 자가튜닝│ 📝 매도 오답노트    │ 🚀 급등락 특이 갭  │
├────────────────────┼─────────────────────┼────────────────────┤
│ 📜 주간 운용보고서 │ 👥 섀도우 모의매매   │ 🚫 격리 쿨다운     │
├────────────────────┼─────────────────────┼────────────────────┤
│ ⏸️ 매수 일시정지   │ ▶️ 매수 재개         │ 🚨 전량 긴급청산   │
└────────────────────────────────────────────────────────┘
```

### 💡 주요 카테고리별 핵심 버튼 가이드

#### 1. 📊 계좌 및 실시간 수익 관리
* **[📊 봇 상태 요약]**: 총 평가 자산, 예수금 잔고, 매매 활성 상태를 3초 만에 브리핑.
* **[📈 보유 포지션 브리핑]**: 현재 보유 중인 종목의 실시간 수익률, 손절선, 1차/2차 목표가 매핑.
* **[💰 실현손익 시리즈]**: 오늘 / 7일 / 30일 / 전체 누적 손익과 승률, 손익비(Profit Factor) 통계.

#### 2. 🚀 종목 발굴 & 퀀트 알파
* **[🚀 실시간 후보 Top 5]**: 3,002개 전 종목 중 5대 직교 팩터 점수가 가장 높은 주도주 5선 (NVDA, PLTR, CEG 등).
* **[👑 주도 테마 1등주]**: AI, 원자력, 방산 등 18대 테마 중 자금 쏠림이 가장 강한 1등 대장주(LEADER 👑).
* **[🎯 스크리너 픽]**: 20일 신고가 돌파 및 칼만 속도 급가속 종목 실시간 포착.

#### 3. 🏛️ 매크로 경제 & D-Day 레이더
* **[🔮 매크로 & 실적 D-Day]**: 
  * 오늘(D-Day) 발표되는 **ADP 민간 비농업 고용, JOLTS 구인건수**
  * 이번 주(D-1~D-2) 예정된 **ISM 서비스업 PMI, 주간 실업수당, 노동부 공식 비농업 고용(NFP)**
  * 다음 주(D-7) 예정된 **CPI 소비자물가지수, FOMC 기준금리 발표일**을 카운트다운 예보.
* **[🏛️ 경제지표 서프라이즈 반응]**: 8대 거시 팩터 점수(+40점 이상 불장)와 실시간 포지션 배수 산출.

#### 4. 🕶️ 스마트머니 & 수급 미세구조
* **[🕶️ 다크풀 장외 매집]**: 월가 대형 기관들이 호가창을 숨겨두고 사들이는 ATS 장외 거래 비중(50% 이상 집중 매집).
* **[🧲 GEX 감마 레이더]**: 마켓메이커의 매수 에어백(Put Wall 지지선)과 매도 저항선(Call Wall) 시각화.
* **[🏛️ 미국 의회 주식 매매]**: 낸시 펠로시 등 미 상·하원 의원들의 내부 정책 수혜주 매수 동향.

---

## 4. 🚨 비상 제어 및 6중 리스크 안전망

### 📱 텔레그램 3대 원격 비상 제어 버튼
1. **`⏸️ 매수 일시정지`**:
   * 즉시 신규 매수 진입을 100% 중단합니다 (기존 보유 종목의 익절/손절 관리는 정상 유지).
   * 여행을 가거나 큰 거시 변동성을 피하고 싶을 때 사용합니다.
2. **`▶️ 매수 재개`**:
   * 일시정지를 해제하고 정상적인 인공지능 자율 매수 모드로 복귀합니다.
3. **`🚨 보유종목 전량 긴급청산`**:
   * 클릭 즉시 시장가로 모든 보유 주식을 전량 매도하여 **100% 현금화**합니다.
   * KIS 증권사 API 직접 주문 폴백이 장착되어 있어 0.1초 만에 안전하게 체결됩니다.

### 🛡️ 계좌를 지키는 6단계 자동 보호 시스템
* **1단계 (개별 손절)**: 진입가 대비 `-3.8%` 또는 ATR 2배 이탈 시 기계적 즉시 손절.
* **2단계 (본절 스탑 Lock)**: 수익률이 `+3.0%` 이상 올라가면 스탑로스를 본절가 위로 올려 무위험 랠리 유지.
* **3단계 (Dead Money 탈출)**: 3~5일간 주가가 오르지 않고 횡보하면 `-0.1%` 내외에서 자동 청산 후 주도주로 교체.
* **4단계 (14일 격리 쿨다운)**: 손절된 종목은 14일간 재매수를 원천 차단하여 감정적 뇌동매매 방지.
* **5단계 (주간 손실 컷)**: 주간 누적 손실이 `-15%`에 도달하면 해당 주 잔여 매매 전면 정지.
* **6단계 (서킷 브레이커)**: 계좌 최대 낙폭(MDD)이 `-25%`에 도달하면 전량 현금화 후 시스템 보호 잠금.

---

## 5. 🧠 5대 직교 퀀트 알파 & 12대 매크로 엔진 원리

### 📐 5대 직교 팩터 종합 점수 모델 (100점 만점)
서로 겹치지 않는 5개의 독립된 팩터를 결합하여 **85점 이상 초우량 종목만 선별**합니다:

1. **🚀 모멘텀 팩터 (25점)**: 2차 칼만 필터 제로랙 추세 속도(\(v_k > +0.5\%/\text{day}\)) 및 20일 신고가 돌파.
2. **🌊 오더플로우 미세구조 (25점)**: 매수 틱 거래량이 매도 대비 2.2배 이상 터진 강력한 기관 매집.
3. **💎 PEAD 실적 드리프트 (20점)**: 어닝 서프라이즈(+15% 이상) 발표 후 기관의 사후 매수 지속성.
4. **🕶️ 스마트머니 수급 (15점)**: SEC 13F 기관 지분율 70% 이상 + 다크풀 장외 매집 비중 50% 이상.
5. **🏛️ 거시경제 팩터 (15점)**: 연준 순유동성 증가 + CPI 안정 + VIX 평온(16pt 이하).

---

## 6. 💎 실전 퀀트 투자 운용 수칙 & 십계명

1. **계좌를 믿고 기계에 맡기세요**: 봇이 현금 100%로 며칠 대기하는 것은 놀고 있는 것이 아니라, 횡보장 속임수(Whipsaw)를 피하는 가장 훌륭한 투자입니다.
2. **손익비(Profit Factor)의 힘을 믿으세요**: 승률이 50%라도, 질 때 `-3%`로 짧게 끊고 이길 때 `+10%~+15%`로 길게 먹으면 계좌는 복리로 폭발적 우상향합니다.
3. **물타기와 몰빵은 영원히 금지됩니다**: 봇은 1개 종목에 최대 33.3%~35% 이상 배팅하지 않으며, 손실 난 종목에 추가 매수를 절대 하지 않습니다.
4. **1차 목표가 도달 시 절반 익절**: `+7.5% ~ +9.0%` 도달 시 50%를 분할 매도하여 수익을 확정 짓고, 나머지는 본절 스탑을 걸어 편안하게 수익을 극대화합니다.

---

## 7. 🛠️ 자주 묻는 질문(FAQ) & 문제 해결

#### Q1. KIS 증권사 토큰은 매일 다시 발급받아야 하나요?
> **A. 아니요, 100% 자동입니다.** 프로그램 내부에 토큰 수명 감시 엔진이 있어 만료 1시간 전에 자동으로 KIS 서버와 통신하여 24시간 무중단 갱신합니다.

#### Q2. 미국 증시 휴장일(공휴일)이나 주말에는 어떻게 되나요?
> **A. 봇이 미국 증시 캘린더를 스스로 체크합니다.** 뉴욕 증시 휴장일에는 자동으로 절전 대기 모드로 전환되며, 장 시작 전 프리마켓부터 다시 깨어나 스캔을 시작합니다.

#### Q3. 스마트폰 텔레그램 버튼을 눌렀는데 반응이 없어요.
> **A.** 오라클 VPS 서버 터미널에서 다음 명령어로 봇 데몬 상태를 점검하세요:
> ```bash
> # 봇 프로세스 확인
> ps aux | grep telegram_interactive_bot
> 
> # 필요시 원클릭 재시작
> pkill -f telegram_interactive_bot.py
> nohup python -u telegram_interactive_bot.py > bot.log 2>&1 &
> ```

---
## 8. ☁️ 오라클 클라우드 VPS 설정 및 배포 가이드

### 8.1 Oracle Cloud 계정 만들기
1. https://cloud.oracle.com/ 에 회원가입 → Free Tier 선택 (VM.Standard.E2.1.Micro 등 무료 인스턴스).
2. 콘솔 → **Compute → Instances** 로 이동 → **Create Instance** 클릭.
3. 이름 지정 (예: `kis-trading-bot`), 이미지 → **Ubuntu 22.04** 선택.
4. Shape → **VM.Standard.E2.1.Micro** (무료).  
5. **SSH Keys** 섹션에서 공개키(`~/.ssh/id_rsa.pub`)를 붙여넣고 **Create**.

### 8.2 SSH 키 생성 및 로컬에 저장
```bash
# 로컬 (Windows) PowerShell에서
ssh-keygen -t rsa -b 4096 -f $HOME\.ssh\oracle_kis_key -N ""   # 비밀번호 없이
# 공개키 확인
cat $HOME\.ssh\oracle_kis_key.pub
```
- 위 공개키를 Oracle Console에 등록하고, 개인키(`oracle_kis_key`)는 로컬에 보관.

### 8.3 로컬에서 VPS에 접속
```bash
ssh -i $HOME\.ssh\oracle_kis_key ubuntu@<Public_IP_of_VPS>
```
- 최초 접속 시 `yes` 입력 후 접속.

### 8.4 시스템 기본 설정 (VPS 내부)
```bash
# 패키지 업데이트
sudo apt update && sudo apt upgrade -y

# Python, git, pip 설치
sudo apt install -y python3 python3-venv python3-pip git

# 필수 라이브러리
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev
```

### 8.5 프로젝트 배포
```bash
# GitHub repo clone
git clone https://github.com/johnjalboss/kis-auto-trading-strategy.git
cd kis-auto-trading-strategy

# 가상환경 생성 & 활성화
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 8.6 .env 파일 설정 (VPS)
- 프로젝트 루트에 `.env` 파일을 생성하고 로컬에서 사용한 내용 그대로 복사.
- 반드시 `KIS_IS_PAPER=false` 를 실제 매매 환경에 맞게 지정.

### 8.7 서비스 자동 실행 (systemd)
`/etc/systemd/system/kis-trading-bot.service` 파일을 만들고 다음 내용 저장:

```ini
[Unit]
Description=KIS Auto Trading Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/kis-auto-trading-strategy
ExecStart=/home/ubuntu/kis-auto-trading-strategy/venv/bin/python -u telegram_interactive_bot.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 서비스 등록 및 시작
sudo systemctl daemon-reload
sudo systemctl enable kis-trading-bot
sudo systemctl start kis-trading-bot

# 상태 확인
sudo systemctl status kis-trading-bot
```

### 8.8 로그 확인 & 재시작
```bash
# 실시간 로그
journalctl -u kis-trading-bot -f

# 재시작
sudo systemctl restart kis-trading-bot
```

### 8.9 방화벽 / 보안그룹 설정
- 인바운드 포트 22(SSH)만 열어두고, 기타 포트는 차단.
- 필요 시 Oracle Cloud 콘솔 → **Virtual Cloud Network → Security Lists** 에서 규칙 추가.

### 8.10 Gemini API (예시) 및 기타 외부 키 발급
- **Gemini** (암호화폐 API) → https://www.gemini.com/api → `API Key`와 `Secret Key` 생성 후 `.env`에 `GEMINI_API_KEY`·`GEMINI_API_SECRET` 추가.
- **Finnhub** → https://finnhub.io/ → `API Key` 발급 후 `.env`에 `FINNHUB_API_KEY` 입력.
- **Alpha Vantage** 등 필요 시 추가 API도 동일 방식으로 `.env`에 기록.

### 8.11 자동 업데이트 (옵션)
```bash
# 매일 02:00에 pull & 재시작
echo "0 2 * * * cd /home/ubuntu/kis-auto-trading-strategy && git pull && sudo systemctl restart kis-trading-bot" | crontab -
```

> **Tip**: `systemctl` 로그와 `bot.log`를 함께 모니터링하면 문제 원인을 빠르게 파악할 수 있습니다.

---
## 9. 🔐 Gemini API (예시) 및 기타 외부 API 키 관리

- **Gemini** (암호화폐 거래소) → https://www.gemini.com/api
  - `API Key`와 `Secret Key`를 생성하고 `.env`에 아래와 같이 추가합니다:
    ```env
    GEMINI_API_KEY=your_gemini_api_key_here
    GEMINI_API_SECRET=your_gemini_api_secret_here
    ```
  - Gemini API는 **REST**와 **WebSocket** 두 가지 방식이 제공됩니다. 실시간 시세를 받으려면 `WebSocket`을, 주문/잔고 조회는 `REST`를 사용합니다.
  - **보안 팁**: API 키는 절대로 코드에 하드코딩하지 말고, `.env` 파일을 `.gitignore`에 포함시켜 버전 관리에서 제외합니다.

- **그 외 API** (예: Alpha Vantage, IEX Cloud, Polygon 등)
  - 각 서비스마다 발급받은 `API Key`를 `.env`에 동일한 형식으로 저장합니다.
  - 키 관리 규칙은 동일하게 **환경 변수**를 통해 주입하고, `dotenv` 라이브러리(`python-dotenv`)가 자동 로드하도록 합니다.

> **Tip**: 로컬 개발 환경과 오라클 VPS 모두 동일한 `.env` 템플릿을 사용하면 배포가 쉬워집니다.

---
*Developed by Deep Quant System & Antigravity AI.*