"""
Configuration Module
====================
Centralized settings for the trading bot.
Loads from .env file and provides defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ==============================================
# KIS API Configuration
# ==============================================

KIS_APP_KEY = os.getenv("KIS_APP_KEY", "")
KIS_APP_SECRET = os.getenv("KIS_APP_SECRET", "")
KIS_CANO = os.getenv("KIS_CANO", "")
KIS_ACNT_PRDT_CD = os.getenv("KIS_ACNT_PRDT_CD", "01")

# Trading mode: VPS=Paper, PROD=Live
TRADING_ENV = os.getenv("TRADING_ENV", "VPS")
IS_PAPER_TRADING = TRADING_ENV.upper() != "PROD"

# Base URL for KIS API
if IS_PAPER_TRADING:
    BASE_URL = "https://openapivts.koreainvestment.com:29443"
else:
    BASE_URL = "https://openapi.koreainvestment.com:9443"

# Token file path
TOKEN_FILE = "token.json"
TOKEN_REFRESH_HOURS = 12

# ==============================================
# Telegram Configuration
# ==============================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ==============================================
# Risk Management
# ==============================================

# Daily stop loss — 스윙 트레이딩: 일일 3% 손실 한도
DAILY_STOP_LOSS_PCT = float(os.getenv("DAILY_STOP_LOSS_PCT", "0.03"))
if DAILY_STOP_LOSS_PCT >= 1.0:
    DAILY_STOP_LOSS_PCT /= 100.0

# Consecutive loss limit — 3번 연속 실패 후 쿨다운
CONSECUTIVE_LOSS_LIMIT = int(os.getenv("CONSECUTIVE_LOSS_LIMIT", "3"))
COOLDOWN_MINUTES = int(os.getenv("COOLDOWN_MINUTES", "60"))

# Position limits
MAX_POSITION_PCT = float(os.getenv("MAX_POSITION_PCT", "0.30"))  # 30% max per position
if MAX_POSITION_PCT >= 1.0:
    MAX_POSITION_PCT /= 100.0
MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", "7"))  # 스윙 최대 7종목 동시 보유

# ==============================================
# Position Upgrade (교체 매매)
# ==============================================

# 새 종목 점수가 보유 종목 점수보다 이 이상 높으면 교체
UPGRADE_SCORE_GAP = int(os.getenv("UPGRADE_SCORE_GAP", "25"))

# 매수 후 최소 보유 시간 (분) — 이 시간 전에는 교체 불가
UPGRADE_MIN_HOLD_MINUTES = int(os.getenv("UPGRADE_MIN_HOLD_MINUTES", "120"))

# 하루 최대 교체 횟수
UPGRADE_MAX_PER_DAY = int(os.getenv("UPGRADE_MAX_PER_DAY", "5"))

# 수익중인 종목은 교체하지 않음 (이 %이상 수익이면 보호)
UPGRADE_PROFIT_PROTECT_PCT = float(os.getenv("UPGRADE_PROFIT_PROTECT_PCT", "0.02"))  # 2%

# ==============================================
# Strategy Parameters
# ==============================================

# Take profit and stop loss — 스윙 트레이딩 기준
# SL: 4% — ATR이 2-3%인 스윙 종목은 2.5%면 노이즈에 매일 털림
# TP: 12% — 스윙은 크게 먹어야 손익비 양수 확보
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "0.12"))   # 12% TP (스윙 표준)
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "0.04"))        # 4% SL (ATR 노이즈 흡수)
BEAR_HARD_STOP_PCT = float(os.getenv("BEAR_HARD_STOP_PCT", "0.03"))  # 약세장 3% 타이트
ATR_STOP_MULTIPLIER = float(os.getenv("ATR_STOP_MULTIPLIER", "1.5"))  # 1.5x ATR
ECON_EVENT_GUARD_ENABLED = False  # Disable daily econ calendar block to trade normally on CPI/PCE days


# Trailing Stop — 스윙: 수익 보호를 넉넉하게
TRAILING_TRIGGER_PCT = float(os.getenv("TRAILING_TRIGGER_PCT", "0.04"))  # 4% 수익부터 트레일링
TRAILING_STOP_PCT = float(os.getenv("TRAILING_STOP_PCT", "0.02"))         # 고점 -2% 트레일링

# Daily trade limit — 스윙 진입 기회 충분히 허용
MAX_DAILY_TRADES = int(os.getenv("MAX_DAILY_TRADES", "15"))

# ==============================================
# BB Squeeze (Screener) Parameters
# ==============================================

# Squeeze 판단 기간 (N일 중 현재 밴드폭 분위 계산)
SQUEEZE_LOOKBACK = int(os.getenv("SQUEEZE_LOOKBACK", "20"))

# Squeeze 임계값 — 하위 X분위 이하이면 스퀴즈 상태로 판단 (0.0~1.0)
SQUEEZE_THRESHOLD = float(os.getenv("SQUEEZE_THRESHOLD", "0.25"))   # 하위 25%

# ==============================================
# Day Type Detection Parameters
# ==============================================

# SPY ADX 임계 — 이 이상이면 추세 장 (원웨이)
DAY_TYPE_ADX_THRESHOLD = float(os.getenv("DAY_TYPE_ADX_THRESHOLD", "20.0"))

# 하락 장 판단 기준 (SPY 당일 변화율 이 이하이면 하락 장)
DAY_TYPE_BEAR_THRESHOLD = float(os.getenv("DAY_TYPE_BEAR_THRESHOLD", "-0.015"))  # -1.5%

# 횡보 장에서 포지션 크기 배수
DAY_TYPE_CHOP_SIZE_MULT = float(os.getenv("DAY_TYPE_CHOP_SIZE_MULT", "0.5"))  # 50% 크기로 줄임

# ==============================================
# Leveraged ETF Safety Rules
# ==============================================

# 레버리지 ETF 목록 (Volatility Decay 위험)
LEVERAGED_ETFS = {
    "TQQQ", "SQQQ", "UPRO", "SPXU", "UDOW", "SDOW",
    "SOXL", "SOXS", "FNGU", "FNGD", "LABU", "LABD",
    "TNA", "TZA", "NUGT", "DUST", "JNUG", "JDST",
    "BULZ", "BERZ", "TECL", "TECS", "FAS", "FAZ",
}

# 인버스 ETF 목록 (하락장 수익용)
INVERSE_ETFS = {
    "SQQQ", "PSQ",   # Nasdaq
    "SPXU", "SH",    # S&P 500
    "SDS",           # S&P 500 2x
    "SOXS",          # Semiconductors
    "LABD",          # Biotech
    "FAZ",           # Financials
    "TZA",           # Small Cap
    "TECS",          # Technology
    "UVXY", "VIXY",  # VIX / Volatility
}

# 방어주 목록 (하락장/약세장 대응용)
DEFENSIVE_UNIVERSE_SET = {
    "PG", "KO", "PEP", "JNJ", "WMT", "COST", "CL", "GIS", "K", "SJM",
    "MO", "PM", "NEE", "DUK", "SO", "ED", "AEP", "XEL", "WEC", "ES",
    "T", "VZ", "CMCSA", "BMY", "ABBV", "MRK", "PFE", "LLY", "ABT"
}


# 방향 반대 레버리지 ETF 쌍 (동시 보유 금지)
CONFLICTING_PAIRS = {
    "TQQQ": "SQQQ", "SQQQ": "TQQQ",
    "UPRO": "SPXU", "SPXU": "UPRO",
    "UDOW": "SDOW", "SDOW": "UDOW",
    "SOXL": "SOXS", "SOXS": "SOXL",
    "FNGU": "FNGD", "FNGD": "FNGU",
    "LABU": "LABD", "LABD": "LABU",
    "TNA": "TZA", "TZA": "TNA",
    "TECL": "TECS", "TECS": "TECL",
    "FAS": "FAZ", "FAZ": "FAS",
}

# 레버리지 ETF 최대 보유 시간 (시간 단위)
LEVERAGED_MAX_HOLD_HOURS = int(os.getenv("LEVERAGED_MAX_HOLD_HOURS", "24"))

# 레버리지 ETF 익절 목표 (일반 종목보다 빠르게)
LEVERAGED_TAKE_PROFIT_PCT = float(os.getenv("LEVERAGED_TAKE_PROFIT_PCT", "0.02"))  # 2%

# ==============================================
# FRED Macro Settings
# ==============================================

# Macro Blind Policy: what to do when FRED API fails or < 7/10 indicators succeed
# PENALTY (default): score = -25 (partial headwind, still allows cautious trading)
# BLOCK:             score = -100 (hard block, no new entries during data blackout)
# NEUTRAL:           score = 0   (ignore macro failure, rely on other signals)
MACRO_BLIND_POLICY = os.getenv("MACRO_BLIND_POLICY", "PENALTY").upper()

RSI_OVERSOLD = int(os.getenv("RSI_OVERSOLD", "30"))
RSI_OVERBOUGHT = int(os.getenv("RSI_OVERBOUGHT", "70"))
MFI_OVERBOUGHT = int(os.getenv("MFI_OVERBOUGHT", "80"))

# ==============================================
# Schedule (KST)
# ==============================================

# Pre-market analysis
PREMARKET_TIME = os.getenv("PREMARKET_TIME", "21:00")

# Main analysis
MACRO_ANALYSIS_TIME = os.getenv("MACRO_ANALYSIS_TIME", "21:30")
SCREENING_TIME = os.getenv("SCREENING_TIME", "22:00")

# Trading session
TRADING_START_TIME = os.getenv("TRADING_START_TIME", "22:30")
CLOSE_ALL_TIME = os.getenv("CLOSE_ALL_TIME", "04:55")

# Reports
DAILY_REPORT_TIME = os.getenv("DAILY_REPORT_TIME", "05:00")

# ==============================================
# Oracle Cloud / System
# ==============================================

# Keep-alive interval (seconds)
KEEPALIVE_INTERVAL = int(os.getenv("KEEPALIVE_INTERVAL", "600"))  # 10 minutes

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "trading_bot.log")

# Database
DB_FILE = os.getenv("DB_FILE", "trades.db")

# Data retention (days)
DATA_RETENTION_DAYS = int(os.getenv("DATA_RETENTION_DAYS", "90"))

# ==============================================
# Screener
# ==============================================

# Max stocks to trade per day
MAX_TARGETS = int(os.getenv("MAX_TARGETS", "5"))

# 스크리너 통과 후 strategy.check_entry()에서 요구하는 최소 신뢰도 점수 (0~100)
# (PhaseConfig.min_entry_score는 장 시간대별 추가 조정됨)
SCREENED_MIN_SCORE = int(os.getenv("SCREENED_MIN_SCORE", "60"))  # 스크리너 통과 종목은 60점 이상

# Minimum price
MIN_STOCK_PRICE = float(os.getenv("MIN_STOCK_PRICE", "5.0"))

# 최대 스크리닝 후보 종목 수 (Russell 1000 대비)
SCREENER_MAX_CANDIDATES = int(os.getenv("SCREENER_MAX_CANDIDATES", "300"))

# ==============================================
# Validation
# ==============================================

def validate_config() -> tuple:
    """Validate critical configuration"""
    errors = []
    warnings = []
    
    if not KIS_APP_KEY or KIS_APP_KEY.startswith("your"):
        errors.append("KIS_APP_KEY not set")
    
    if not KIS_APP_SECRET or KIS_APP_SECRET.startswith("your"):
        errors.append("KIS_APP_SECRET not set")
    
    if not KIS_CANO:
        errors.append("KIS_CANO (account number) not set")
    
    if not TELEGRAM_BOT_TOKEN:
        warnings.append("TELEGRAM_BOT_TOKEN not set (notifications disabled)")
    
    if not TELEGRAM_CHAT_ID:
        warnings.append("TELEGRAM_CHAT_ID not set (notifications disabled)")
    
    return errors, warnings


def print_config():
    """Print current configuration"""
    print("=" * 50)
    print("CONFIGURATION")
    print("=" * 50)
    print(f"Trading Mode: {'PAPER' if IS_PAPER_TRADING else 'LIVE'}")
    print(f"Account: {KIS_CANO[:4]}****" if KIS_CANO else "Not set")
    print(f"Telegram: {'Enabled' if TELEGRAM_BOT_TOKEN else 'Disabled'}")
    print(f"Daily Stop: {DAILY_STOP_LOSS_PCT:.0%}")
    print(f"Max Position: {MAX_POSITION_PCT:.0%}")
    print(f"Max Targets: {MAX_POSITIONS}")
    print("=" * 50)


if __name__ == "__main__":
    print_config()
    
    errors, warnings = validate_config()
    
    if errors:
        print("\n⛔ ERRORS:")
        for e in errors:
            print(f"  - {e}")
    
    if warnings:
        print("\n⚠️ WARNINGS:")
        for w in warnings:
            print(f"  - {w}")
