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
INITIAL_CAPITAL = float(os.getenv("INITIAL_CAPITAL", "766.49"))

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

# Per-position strict stop loss (-6.0% wide stop floor to let high-momentum runners run)
STOP_LOSS_PCT = 0.060

# Consecutive loss limit — 대표님 요구사항 반영: 불필요한 3연속 손실 쿨다운 매매 차단 기능 비활성화 (False)
ENABLE_CONSECUTIVE_LOSS_COOLDOWN = False
CONSECUTIVE_LOSS_LIMIT = int(os.getenv("CONSECUTIVE_LOSS_LIMIT", "999"))
COOLDOWN_MINUTES = int(os.getenv("COOLDOWN_MINUTES", "0"))

# Position limits (공격형 고수익 모드: 3개 상위 주도주 각 33.3% 집중 투자)
MAX_POSITION_PCT = float(os.getenv("MAX_POSITION_PCT", "0.333"))  # 33.3% max per position
if MAX_POSITION_PCT >= 1.0:
    MAX_POSITION_PCT /= 100.0
MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", "3"))  # 3종목 집중 투자 원칙 (+2,048% CAGR 모델)

# Dynamic .env parameters
MIN_ENTRY_SCORE = int(os.getenv("MIN_ENTRY_SCORE", "60"))
DAILY_STOP_LOSS_PCT = float(os.getenv("DAILY_STOP_LOSS_PCT", "0.05"))
if DAILY_STOP_LOSS_PCT >= 1.0:
    DAILY_STOP_LOSS_PCT /= 100.0

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
FRED_API_KEY = os.getenv("FRED_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DISABLE_OPTIONS_FLOW = os.getenv("DISABLE_OPTIONS_FLOW", "false").lower() in ("true", "1", "yes")
DISABLE_YFINANCE_FALLBACK = os.getenv("DISABLE_YFINANCE_FALLBACK", "false").lower() in ("true", "1", "yes")

# ==============================================
# [ENABLED] UPGRADE 교체매매 활성화 — 최소 30점 차이날 때만 교체
# 너무 자주 발생하는 것을 방지하기 위해 큰 점수 격차(30점)를 설정하여 무분별한 교체를 방지합니다.
UPGRADE_SCORE_GAP = int(os.getenv("UPGRADE_SCORE_GAP", "30"))  # 스윙 포지션 무분별 교체 방지

# 매수 후 최소 보유 시간 (분)
UPGRADE_MIN_HOLD_MINUTES = int(os.getenv("UPGRADE_MIN_HOLD_MINUTES", "120"))

# 하루 최대 교체 횟수
UPGRADE_MAX_PER_DAY = int(os.getenv("UPGRADE_MAX_PER_DAY", "1"))  # 1회: 스윙 포지션 안정성 최우선

# 수익중인 종목은 교체하지 않음 (이 %이상 수익이면 보호)
UPGRADE_PROFIT_PROTECT_PCT = float(os.getenv("UPGRADE_PROFIT_PROTECT_PCT", "0.02"))  # 2%

# 손실중인 종목 교체 매도 금지 기준선 (이 % 이하 손실이면 교체 금지, 예: -0.005 = -0.5% 이하 손실 포지션 교체 절대 금지)
UPGRADE_LOSS_LIMIT_PCT = float(os.getenv("UPGRADE_LOSS_LIMIT_PCT", "-0.005"))

# ==============================================
# Continuous Real-Time Streaming Screener (Zero Resting Time)
# ==============================================
SCREENER_CACHE_MINUTES = int(os.getenv("SCREENER_CACHE_MINUTES", "5"))  # 5: Ultra-fast 5-min intraday full universe re-scan

# ==============================================
# Strategy & Profit Execution Parameters
# ==============================================

# [PROFIT MAXIMIZER] 분할 익절 및 무위험 본절 스탑 파라미터 (v4.0)
PARTIAL_TAKE_PROFIT_PCT = float(os.getenv("PARTIAL_TAKE_PROFIT_PCT", "0.05"))  # +5.0% 50% 분할익절
BREAKEVEN_STOP_TRIGGER  = float(os.getenv("BREAKEVEN_STOP_TRIGGER", "0.035"))   # +3.5% 달성 시 손절가를 본절가로 상향

TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "0.15"))       # 15% 최종 TP
STOP_LOSS_PCT = 0.045                                                   # -4.5% safety hard SL
BEAR_HARD_STOP_PCT = 0.045                                              # -4.5% safety bear SL
ATR_STOP_MULTIPLIER = float(os.getenv("ATR_STOP_MULTIPLIER", "2.2")) # 2.2x ATR dynamic stop
ECON_EVENT_GUARD_ENABLED = False

# Trailing Stop — +5.5% 수익 이상부터 트레일링 적용
TRAILING_TRIGGER_PCT = float(os.getenv("TRAILING_TRIGGER_PCT", "0.055"))
TRAILING_STOP_PCT = float(os.getenv("TRAILING_STOP_PCT", "0.025"))

# Daily trade limit
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

# Leveraged/Inverse ETF Overnight Risk Control
# False (Default): Hold positions overnight to capture gap-up profits, monitored continuously for dynamic stop-loss execution.
OVERNIGHT_LEVERAGE_EXIT = False
LEVERAGED_STOP_LOSS_PCT = 0.040

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

# 방어주 및 헬스케어/금융/가치주 목록 (하락장/약세장 수급 유입주 — 강제 청산 대상 제외)
DEFENSIVE_UNIVERSE_SET = {
    "PG", "KO", "PEP", "JNJ", "WMT", "COST", "CL", "GIS", "K", "SJM",
    "MO", "PM", "NEE", "DUK", "SO", "ED", "AEP", "XEL", "WEC", "ES",
    "T", "VZ", "CMCSA", "BMY", "ABBV", "MRK", "PFE", "LLY", "ABT",
    "AVTR", "NVO", "FNB", "GEO", "UNH", "CVS", "GILD", "AMGN", "REGN", "CI", "HUM", "MCK", "CAH"
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

# Trading session (Full 15-Hour Continuous Monitoring: Premarket 18:00 -> Main 22:30 -> Aftermarket 09:00 KST)
TRADING_START_TIME = os.getenv("TRADING_START_TIME", "18:00")
CLOSE_ALL_TIME = os.getenv("CLOSE_ALL_TIME", "09:00")

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

# 최대 스크리닝 후보 종목 수 (초고속 실시간 반응성 최적화: 75종목)
SCREENER_MAX_CANDIDATES = int(os.getenv("SCREENER_MAX_CANDIDATES", "75"))

# 스크리너 캐시 주기 (분 단위) — 15분 주기로 단축하여 기회포착 극대화
SCREENER_CACHE_MINUTES = int(os.getenv("SCREENER_CACHE_MINUTES", "15"))


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
