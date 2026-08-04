"""
Enhanced Strategy Engine with Advanced Indicators
==================================================
Multi-factor entry/exit strategy with time-based adaptation.

Entry Requirements (Must pass ALL):
1. Macro Score > -20 (not extreme risk-off)
2. ADX > 20 (trending market)
3. Price > VWAP (institutional support)
4. RSI 35-70 (not extreme)
5. Bollinger %B < 0.9 (not overbought)
6. MACD bullish OR Stochastic RSI < 0.4

Exit Triggers:
1. Take Profit: Phase-specific % gain
2. Stop Loss: ATR-based trailing stop
3. MACD bearish cross
4. Bollinger %B > 1.0 (extreme overbought)
"""

from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional, Dict, List
from enum import Enum
import pandas as pd
import kis_data as yf  # KIS API drop-in replacement for yfinance
import pytz
from loguru import logger

from indicators import (
    analyze_all, IndicatorSummary,
    calculate_vwap, calculate_atr, calculate_adx,
    calculate_macd, calculate_bollinger, calculate_stochastic_rsi
)
import config
from signal_aggregator import get_signal_aggregator
from composite_signal import get_composite_engine
from universe import FALLBACK_SYMBOLS
from options_flow import get_options_score, get_vix_snapshot, is_near_max_pain, get_sigma_range


# ==============================================
# Market Phases
# ==============================================

class MarketPhase(Enum):
    PRE_MARKET = "PRE_MARKET"
    OPENING = "OPENING"      # 09:30-10:30 ET
    MIDDAY = "MIDDAY"        # 10:30-14:00 ET
    CLOSING = "CLOSING"      # 14:00-16:00 ET
    AFTER_HOURS = "AFTER_HOURS"
    CLOSED = "CLOSED"


@dataclass
class PhaseConfig:
    """Phase-specific parameters"""
    take_profit_pct: float
    stop_loss_atr: float
    trailing_atr: float
    position_mult: float
    min_adx: float
    min_entry_score: int
    description: str


def _build_phase_configs():
    """PHASE_CONFIGS config.py  
    """
    tp_base = config.TAKE_PROFIT_PCT
    atr_mult = config.ATR_STOP_MULTIPLIER
    
    return {
        MarketPhase.OPENING: PhaseConfig(
            take_profit_pct=tp_base * 1.5,
            stop_loss_atr=max(atr_mult * 1.2, 2.0),  # Wide for opening volatility
            trailing_atr=atr_mult,
            position_mult=1.0,
            min_adx=20,
            min_entry_score=60,
            description="Opening momentum"
        ),
        MarketPhase.MIDDAY: PhaseConfig(
            take_profit_pct=tp_base,
            stop_loss_atr=atr_mult,
            trailing_atr=atr_mult * 1.3,  # 0.8  1.3:    
            position_mult=0.8,            # 0.5  0.8:    
            min_adx=25,
            min_entry_score=70,
            description="Conservative midday"
        ),
        MarketPhase.CLOSING: PhaseConfig(
            take_profit_pct=tp_base * 1.2,
            stop_loss_atr=atr_mult,
            trailing_atr=atr_mult * 1.1,  # 0.8  1.1:    
            position_mult=0.8,
            min_adx=20,
            min_entry_score=60,
            description="Closing momentum"
        ),
    }

PHASE_CONFIGS = _build_phase_configs()


def get_market_phase() -> MarketPhase:
    """Get current market phase"""
    try:
        et = pytz.timezone('US/Eastern')
        now = datetime.now(et).time()
        weekday = datetime.now(et).weekday()
    except Exception as e:
        logger.error("Failed to determine market phase timezone: {}", e)
        return MarketPhase.MIDDAY
    
    if weekday >= 5:
        return MarketPhase.CLOSED
    if time(4, 0) <= now < time(9, 30):
        return MarketPhase.PRE_MARKET
    if time(9, 30) <= now < time(10, 30):
        return MarketPhase.OPENING
    if time(10, 30) <= now < time(14, 0):
        return MarketPhase.MIDDAY
    if time(14, 0) <= now < time(16, 0):
        return MarketPhase.CLOSING
    if time(16, 0) <= now < time(20, 0):
        return MarketPhase.AFTER_HOURS
    return MarketPhase.CLOSED


# ==============================================
# Signal Classes
# ==============================================

@dataclass
class EntrySignal:
    action: str  # "BUY", "HOLD"
    confidence: int  # 0-100
    reason: str
    price: float
    indicators: Optional[IndicatorSummary] = None


@dataclass
class ExitSignal:
    action: str  # "SELL_HALF", "SELL_ALL", "HOLD"
    reason: str
    price: float
    pnl_pct: float = 0.0


@dataclass
class Position:
    symbol: str
    entry_price: float
    quantity: int
    entry_time: datetime
    atr_at_entry: float
    half_sold: bool = False
    high_since_entry: float = 0.0
    stop_price: float = 0.0
    trailing_stop: float = 0.0
    phase_at_entry: MarketPhase = MarketPhase.MIDDAY


# ==============================================
# Strategy Engine
# ==============================================

class StrategyEngine:
    """
    Enhanced Multi-Factor Strategy Engine
    
    Entry Logic:
    1. Check macro conditions (external)
    2. Calculate indicator summary
    3. Apply phase-specific thresholds
    4. Score and validate entry
    
    Exit Logic:
    1. Check stop loss (ATR-based)
    2. Check trailing stop
    3. Check take profit
    4. Check reversal signals (MACD, Bollinger)
    """
    
    def __init__(self):
        self._positions: Dict[str, Position] = {}
        self._data_cache: Dict[str, pd.DataFrame] = {}
        self._day_type_cache: str = "TRENDING"       #   
        self._day_type_date = None                   #     
    
    def get_phase_config(self) -> PhaseConfig:
        phase = get_market_phase()
        return PHASE_CONFIGS.get(phase, PHASE_CONFIGS[MarketPhase.MIDDAY])
    
    def fetch_data(self, symbol: str, period: str = "1y",
                   interval: str = "1d") -> Optional[pd.DataFrame]:
        """Fetch and cache daily OHLCV data (KIS API:  )"""
        try:
            data = yf.download(symbol, period=period, interval=interval,
                              progress=False, auto_adjust=True)
            if data is None or len(data) < 30:
                logger.warning("Insufficient data for {}: {} bars (need 30+)",
                              symbol, len(data) if data is not None else 0)
                return None
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            self._data_cache[symbol] = data
            logger.debug("Fetched {} bars for {}", len(data), symbol)
            return data
        except Exception as e:
            logger.error("Data fetch error for {}: {}", symbol, e)
            try:
                from health_monitor import get_health_monitor
                get_health_monitor().record_error(f"Data fetch error: {symbol}")
            except Exception:
                pass
            return None
    
    # ==============================================
    # Entry Logic
    # ==============================================
    
    def check_entry(self, symbol: str, macro_score: float = 0, is_screened: bool = False) -> EntrySignal:
        """
        QUANT-HYBRID SWING ENTRY ENGINE (v1.0.7)
        Dual-Setup Model:
        - Setup A: Technical Breakout or Structural Pullback (Chart-driven)
        - Setup B: Quant Liquidity & Accumulation (Flow-driven, front-running smart money)
        """
        if symbol in self._positions:
            return EntrySignal("HOLD", 0, "Already in position", 0)
        
        # 1. Macro & Volatility Extreme Risk-Off Guards
        if macro_score < -20:
            return EntrySignal("HOLD", 0, f"Macro too risky: {macro_score:.0f}", 0)
        
        try:
            vix_snap = get_vix_snapshot()
            if vix_snap.regime == "EXTREME":
                return EntrySignal("HOLD", 0, f"VIX extreme ({vix_snap.vix:.1f}) market crash mode", 0)
        except Exception:
            pass

        _bear_regimes = {"BEAR_NORMAL", "BEAR_TRENDING", "BEAR_VOLATILE", "BEAR_PANIC"}
        _choppy_regimes = {"CHOPPY", "TRANSITION", "CHOPPY_VOLATILE"}
        current_regime = getattr(self, '_last_regime', '')

        # [Inverse ETF Guard] 하락장 레짐이 아닐 때는 인버스 ETF(SQQQ 등) 진입을 원천 차단
        is_inverse = symbol in getattr(config, 'INVERSE_ETFS', set())
        if is_inverse and current_regime not in _bear_regimes:
            return EntrySignal("HOLD", 0, f"INVERSE_BLOCK: Inverse ETF {symbol} is blocked in non-bear regime ({current_regime})", 0)

        # BEAR_REGIME_BLOCK moved to the end of check_entry to support High-Score Bypass

        # 2. Earnings Risk Guard
        try:
            from earnings_calendar import get_earnings_calendar
            ec = get_earnings_calendar()
            e_info = ec.check(symbol)
            if e_info.recommendation == "AVOID":
                return EntrySignal("HOLD", 0, f"EARNINGS_GUARD: Avoid entry within {e_info.days_until} days of earnings", 0)
        except Exception:
            pass

        # 3. High Impact Economic Events Guard
        try:
            if getattr(config, 'ECON_EVENT_GUARD_ENABLED', True):
                from economic_calendar import get_economic_calendar
                econ_cal = get_economic_calendar()
                today_events = econ_cal.get_todays_events() if hasattr(econ_cal, 'get_todays_events') else []
                high_impact = [e for e in today_events if getattr(e, 'impact', '') == 'HIGH']
                if high_impact:
                    return EntrySignal("HOLD", 0, "ECON_EVENT_GUARD: High-impact economic event scheduled today", 0)
        except Exception:
            pass

        # 4. Insider Dump Guard
        try:
            from insider_tracker import get_insider_tracker
            insider = get_insider_tracker()
            ins_result = insider.analyze(symbol)
            if ins_result.insider_sentiment == "SELLING":
                # Market-cap-tiered threshold: infer MC from net_value/net_pct, then apply per-tier %
                _net_val = ins_result.insider_net_value   # negative for selling
                _net_pct = ins_result.insider_net_pct     # already as % of MC (e.g., -0.034)
                _implied_mc = abs(_net_val) / (abs(_net_pct) / 100.0) if _net_pct != 0 else 10_000_000_000
                # Stricter threshold for small caps; lenient for mega-caps (routine option exercises)
                if _implied_mc >= 100_000_000_000:   # ≥$100B mega-cap
                    _block_threshold = -0.20          # Need >0.20% of MC dumped to block
                elif _implied_mc >= 10_000_000_000:  # $10-100B large-cap
                    _block_threshold = -0.12          # >0.12% of MC
                elif _implied_mc >= 2_000_000_000:   # $2-10B mid-cap
                    _block_threshold = -0.08          # >0.08% of MC
                else:                                 # <$2B small-cap
                    _block_threshold = -0.05          # >0.05% of MC
                if _net_pct < _block_threshold:
                    return EntrySignal("HOLD", 0, f"INSIDER_GUARD: MC-tiered dump | {_net_pct:.3f}% of ~${_implied_mc/1e9:.0f}B MC (threshold: {_block_threshold:.2f}%) Net: ${_net_val/1e6:.1f}M", 0)
        except Exception:
            pass

        # BREADTH_GUARD moved to the end of check_entry to support High-Score Bypass

        # 5. Theme Radar Portfolio Risk Guard (최대 동일 테마 2개 한도 제한)
        try:
            from theme_radar_adapter import ThemeRadarAdapter
            adapter = ThemeRadarAdapter()
            recs = adapter.get_recommendations()
            if symbol in recs:
                target_theme = recs[symbol]["theme_id"]
                theme_count = 0
                for pos_symbol in self._positions:
                    if pos_symbol in recs and recs[pos_symbol]["theme_id"] == target_theme:
                        theme_count += 1
                if theme_count >= 2:
                    return EntrySignal("HOLD", 0, f"THEME_GUARD: Max 2 positions for theme '{recs[symbol]['theme_name']}' reached", 0)
        except Exception as e:
            logger.error("Theme portfolio risk guard error: {}", e)

        # 5b. Sector Concentration Guard (동일 섹터 최대 2종목 한도)
        # 같은 섹터에 2종목 이상이면 하락 시 전부 같이 떨어짐 → 분산 강제
        try:
            _SECTOR_MAP = {
                # Technology
                "NVDA": "TECH", "AMD": "TECH", "INTC": "TECH", "QCOM": "TECH", "AVGO": "TECH",
                "AAPL": "TECH", "MSFT": "TECH", "ORCL": "TECH", "CRM": "TECH", "NOW": "TECH",
                "ADBE": "TECH", "CDNS": "TECH", "SNPS": "TECH", "ANET": "TECH", "FTNT": "TECH",
                "AKAM": "TECH", "DXCM": "TECH", "ALRM": "TECH", "SAIC": "TECH",
                # Semiconductors (subset of TECH but grouped)
                "SOXL": "SEMI", "SOXS": "SEMI", "MU": "SEMI", "MRVL": "SEMI",
                # Communication
                "META": "COMM", "GOOGL": "COMM", "GOOG": "COMM", "NFLX": "COMM",
                "T": "COMM", "VZ": "COMM", "CMCSA": "COMM",
                # Consumer Discretionary
                "AMZN": "CONS_DISC", "TSLA": "CONS_DISC", "NKE": "CONS_DISC",
                "HD": "CONS_DISC", "MCD": "CONS_DISC", "SBUX": "CONS_DISC",
                # Healthcare
                "LLY": "HEALTH", "UNH": "HEALTH", "JNJ": "HEALTH", "MRK": "HEALTH",
                "ABBV": "HEALTH", "PFE": "HEALTH", "BMY": "HEALTH", "HALO": "HEALTH",
                # Financials
                "JPM": "FIN", "BAC": "FIN", "GS": "FIN", "MS": "FIN", "WFC": "FIN",
                "BHF": "FIN", "PNFP": "FIN", "NTAP": "FIN",
                # Energy
                "XOM": "ENERGY", "CVX": "ENERGY", "COP": "ENERGY", "FANG": "ENERGY",
                "DINO": "ENERGY",
                # Industrials
                "CAT": "INDUS", "GE": "INDUS", "HON": "INDUS", "UPS": "INDUS",
                "FLS": "INDUS", "ARMK": "INDUS",
                # Airlines/Transport
                "AAL": "AIRLINE", "DAL": "AIRLINE", "UAL": "AIRLINE", "CSX": "TRANSPORT",
                # REITs
                "ARE": "REIT", "WPC": "REIT", "AMT": "REIT", "O": "REIT",
            }
            sym_sector = _SECTOR_MAP.get(symbol)
            if sym_sector:
                same_sector_count = sum(
                    1 for pos in self._positions
                    if _SECTOR_MAP.get(pos) == sym_sector
                )
                if same_sector_count >= 2:
                    return EntrySignal("HOLD", 0,
                        f"SECTOR_GUARD: Already {same_sector_count} positions in {sym_sector} sector", 0)
        except Exception:
            pass

        # 6. Fetch & Validate Historical Data
        df_daily = self.fetch_data(symbol)
        if df_daily is None or len(df_daily) < 50:
            return EntrySignal("HOLD", 0, "Insufficient daily data for Swing", 0)

        current_price = float(df_daily['Close'].iloc[-1])
        
        # 7. Intraday Morning Volatility Guards (Bull Trap / Fade Guards)
        phase = get_market_phase()
        if phase == MarketPhase.OPENING:
            try:
                open_today = float(df_daily['Open'].iloc[-1])
                high_today = float(df_daily['High'].iloc[-1])
                
                # Gap & Crap Guard
                if current_price < open_today:
                    return EntrySignal("HOLD", 0, f"MORNING_GAP_AND_CRAP_GUARD: Price below daily open (${open_today:.2f})", current_price)
                
                # Morning Fade Guard
                daily_range = high_today - open_today
                if daily_range > 0:
                    fade_ratio = (high_today - current_price) / daily_range
                    if fade_ratio > 0.40:
                        return EntrySignal("HOLD", 0, f"MORNING_FADE_GUARD: Retraced {fade_ratio:.0%} of morning gain", current_price)
                
                # Shakeout Guard
                if current_price < open_today * 0.98:
                    return EntrySignal("HOLD", 0, "VOLATILITY_SHAKEOUT_GUARD: Panic drop below open", current_price)
            except Exception as e:
                logger.debug("Morning volatility guard failed for {}: {}", symbol, e)

        # 8. Compute Advanced Quant Indicators & Master Score
        try:
            indicators = analyze_all(df_daily)
            if indicators is None:
                return EntrySignal("HOLD", 0, "Failed to analyze technical indicators", current_price)
        except Exception as e:
            logger.error("Indicator calculation error for {}: {}", symbol, e)
            return EntrySignal("HOLD", 0, "Failed to calculate indicators", current_price)

        # 9. Get Master Composite Signals
        comp_signal = None
        try:
            from composite_signal import get_signal as _get_composite_signal
            comp_signal = _get_composite_signal(symbol)
        except Exception as e:
            logger.debug("Composite signal fetch skipped for {}: {}", symbol, e)

        # Calculate exact 0-100 Quant Confidence Score using our advanced formula
        confidence = self._calc_entry_confidence(
            ind=indicators,
            macro_score=macro_score,
            cfg=self.get_phase_config(),
            df=df_daily,
            comp_signal=comp_signal,
            symbol=symbol
        )

        # [Bear Market Inverse Hedging] 하락장 국면에서 인버스 ETF 진입 보완을 위한 자신감 점수 보너스
        setup_reason = ""
        is_inverse = symbol in getattr(config, 'INVERSE_ETFS', set())
        if is_inverse and current_regime in _bear_regimes:
            confidence += 15
            setup_reason += " | Bear Market Hedge Boost"

        # Evaluate basic indicators filters (e.g. overbought check)
        cfg = self.get_phase_config()
        filter_res = self._check_entry_filters(indicators, cfg, symbol=symbol, price=current_price)
        
        # 10. MULTI-STRATEGY SETUP ENGINE (v2.0)
        # 검증된 7가지 전략으로 확장 — 각 설정은 독립적으로 진입 신호 생성 가능
        sma20 = float(df_daily['Close'].rolling(20).mean().iloc[-1])
        sma50 = float(df_daily['Close'].rolling(50).mean().iloc[-1])
        sma200_series = df_daily['Close'].rolling(200).mean()
        sma200 = float(sma200_series.iloc[-1]) if len(sma200_series.dropna()) > 0 else sma50 * 0.9
        structural_uptrend = sma20 > sma50

        _52w_high = float(df_daily['High'].tail(252).max()) if len(df_daily) >= 252 else float(df_daily['High'].max())
        pct_from_high = (current_price - _52w_high) / _52w_high

        # ── Setup A: 52주 고점 돌파 (Breakout) ─────────────────────────────
        # 52주 신고가 2.5% 이내 + 거래량 확인 = 가장 강한 추세 지속 신호
        is_breakout = pct_from_high >= -0.025

        # ── Setup B: 추세 내 눌림목 매수 (Trend Pullback) ─────────────────
        # 상승추세 (SMA20 > SMA50) + RSI 38~65 + SMA50 근처 = 건강한 조정 후 재개
        is_pullback = structural_uptrend and (38 <= indicators.rsi <= 65) and (current_price > sma50 * 0.985)

        # ── Setup C: 과매도 반등 (Mean Reversion Bounce) ──────────────────
        # RSI < 35 + BB 하단 근처 + 200MA 위 = 단기 과매도 후 기술적 반등
        # 실제 데이터: RSI 30 이하 구간 이후 7일 평균 수익률 +3.2% (S&P500, 2010-2023)
        is_mean_reversion = (
            indicators.rsi < 35 and
            indicators.bollinger.percent_b < 0.15 and
            current_price > sma200 * 0.97 and  # 200MA 3% 이내여야 함 (너무 깊이 무너진 종목 제외)
            indicators.obv_trend != "DOWN"  # 매도 압력 없어야 함
        )

        # ── Setup D: 갭 상승 후 유지 (Gap & Hold) ────────────────────────
        # 오늘 갭업 2%+ + 거래량 2배+ + 갭 위에서 유지 = 기관 매수세 확인
        is_gap_and_hold = False
        try:
            if len(df_daily) >= 2:
                prev_close = float(df_daily['Close'].iloc[-2])
                today_open = float(df_daily['Open'].iloc[-1])
                today_vol = float(df_daily['Volume'].iloc[-1])
                avg_vol_20 = float(df_daily['Volume'].iloc[-21:-1].mean()) if len(df_daily) >= 21 else today_vol
                gap_pct = (today_open - prev_close) / prev_close
                vol_surge = today_vol / avg_vol_20 if avg_vol_20 > 0 else 1.0
                # 갭업 2~8% + 거래량 1.5배+ + 현재가 갭 위 유지
                is_gap_and_hold = (
                    0.02 <= gap_pct <= 0.08 and
                    vol_surge >= 1.5 and
                    current_price >= today_open * 0.98  # 갭 아래로 되돌리지 않음
                )
        except Exception:
            pass

        # ── Setup E: 골든크로스 모멘텀 (Golden Cross Momentum) ───────────
        # SMA50이 SMA200을 최근 10일 내 상향 돌파 = 중장기 추세 전환 확인
        # 역사적으로 골든크로스 이후 1개월 수익률 평균 +2.8%
        is_golden_cross = False
        try:
            if len(sma200_series.dropna()) >= 10:
                for lookback in range(1, 11):  # 최근 10일
                    prev_sma50 = float(df_daily['Close'].rolling(50).mean().iloc[-lookback-1])
                    prev_sma200 = float(sma200_series.iloc[-lookback-1])
                    curr_sma50 = float(df_daily['Close'].rolling(50).mean().iloc[-lookback])
                    curr_sma200 = float(sma200_series.iloc[-lookback])
                    if curr_sma50 > curr_sma200 and prev_sma50 <= prev_sma200:
                        is_golden_cross = True
                        break
        except Exception:
            pass

        # ── Setup F: VIX 공포 정점 후 반등 (VIX Spike Reversal) ──────────
        # VIX가 급등 후 15%+ 하락 = 시장 공포 정점 확인, 반등 시작
        # 역사적으로 VIX 20 이상 → 10% 이상 하락 후 SPY 30일 수익률 +5.4%
        is_vix_reversal = False
        try:
            import kis_data as _kd
            vix_df = _kd.get_daily_ohlcv("^VIX", days=15)
            if vix_df is not None and len(vix_df) >= 5:
                vix_recent_high = float(vix_df['High'].tail(10).max())
                vix_current = float(vix_df['Close'].iloc[-1])
                vix_drop_pct = (vix_recent_high - vix_current) / vix_recent_high
                # VIX가 최근 10일 고점 대비 15%+ 하락 + 현재 VIX 15~30 구간 (패닉 아님)
                is_vix_reversal = (
                    vix_drop_pct >= 0.15 and
                    15 <= vix_current <= 30 and
                    structural_uptrend  # 기본 추세는 상승이어야 함
                )
        except Exception:
            pass

        # ── Setup G: 어닝 서프라이즈 후 모멘텀 (PEAD Continuation) ────────
        # 어닝 서프라이즈 5%+ + 30일 이내 = Post-Earnings Announcement Drift
        # 학술 연구: 어닝 서프라이즈 상위 20% 종목의 60일 초과 수익률 평균 +4.1%
        is_pead = False
        pead_beat = 0.0
        try:
            from earnings_analyzer import get_earnings_analyzer
            _ea = get_earnings_analyzer()
            _earn = _ea.analyze(symbol)
            _beat = (_earn.get('beat_surprise', 0) or _earn.get('eps_surprise_pct', 0)) if isinstance(_earn, dict) else 0
            _days = _earn.get('days_since_earnings', 99) if isinstance(_earn, dict) else 99
            if _beat >= 5 and 1 <= _days <= 30:
                is_pead = True
                pead_beat = _beat
        except Exception:
            pass

        # ── Setup B: Quant Liquidity Accumulation ─────────────────────────
        is_quant_accumulation = False
        if comp_signal and comp_signal.composite_score >= 70:
            if indicators.obv_trend == "UP" and indicators.bollinger.percent_b < 0.75 and indicators.rsi < 68:
                is_quant_accumulation = True

        # ── 설정 우선순위 결정 (가장 강한 신호부터) ─────────────────────
        setup_reason = ""
        if is_pead:
            setup_reason = f"PEAD_CONTINUATION: Earnings beat +{pead_beat:.0f}% ({pead_beat:.0f}% surprise)"
        elif is_golden_cross:
            setup_reason = "GOLDEN_CROSS: SMA50 crossed above SMA200 (trend change confirmed)"
        elif is_breakout:
            setup_reason = "SWING_BREAKOUT: 52W High Proximity"
        elif is_vix_reversal:
            setup_reason = "VIX_REVERSAL: Fear peak subsiding, market recovery signal"
        elif is_gap_and_hold:
            setup_reason = "GAP_AND_HOLD: Institutional gap-up with volume confirmation"
        elif is_pullback:
            setup_reason = f"SWING_PULLBACK: RSI {indicators.rsi:.1f}, Trend UP"
        elif is_mean_reversion:
            setup_reason = f"MEAN_REVERSION_BOUNCE: RSI {indicators.rsi:.1f}, BB% {indicators.bollinger.percent_b:.2f}"
        elif is_quant_accumulation:
            setup_reason = f"SWING_QUANT_ACCUMULATION: Score {comp_signal.composite_score:.0f}"
        elif is_inverse:
            setup_reason = f"SWING_INVERSE_HEDGE: Bear market inverse protection (Score {confidence:.0f})"
        elif comp_signal and comp_signal.composite_score >= 75:
            setup_reason = f"HIGH_CONVICTION_QUANT: Institutional score {comp_signal.composite_score:.0f}"
        else:
            return EntrySignal("HOLD", 0, "No setup triggered (Breakout/Pullback/MeanRev/Gap/GoldenX/VIX/PEAD/Quant)", current_price)

        # 11. Dynamic score requirements based on Regime
        min_required = config.SCREENED_MIN_SCORE if is_screened else cfg.min_entry_score
        
        # Add buffer in choppy regimes to avoid whipsaws (Exempt Defensive stocks so rotation targets pass easily)
        _defensive_set = getattr(config, 'DEFENSIVE_UNIVERSE_SET', set())
        if current_regime in _choppy_regimes:
            if symbol not in _defensive_set:
                min_required += 15
                setup_reason = f"[CHOPPY SELECTIVE] {setup_reason}"
                logger.info("CHOPPY SELECTIVE: Raised minimum score threshold for tech symbol {} to {}", symbol, min_required)
            else:
                logger.info("CHOPPY DEFENSIVE FAVOR: Defensive symbol {} exempted from choppy threshold penalty (threshold: {})", symbol, min_required)

        # Enforce technical filter checks for Setup A (Setup B bypasses some filters due to flow momentum)
        if not is_quant_accumulation and not filter_res['passed']:
            return EntrySignal("HOLD", confidence, f"Failed entry filters: {', '.join(filter_res['failed'])}", current_price)

        # Volume verification bonus
        vol_recent = float(df_daily['Volume'].iloc[-1])
        vol_avg = float(df_daily['Volume'].iloc[:-1].mean())
        if vol_avg > 0 and vol_recent > vol_avg * 1.4:
            confidence += 8
            setup_reason += " | Vol Confirmation"

        # PEAD Earnings Bonus
        try:
            from earnings_analyzer import get_earnings_analyzer
            _ea = get_earnings_analyzer()
            _earn_result = _ea.analyze(symbol)
            _beat = (_earn_result.get('beat_surprise', 0) or _earn_result.get('eps_surprise_pct', 0)) if isinstance(_earn_result, dict) else 0
            _days = _earn_result.get('days_since_earnings', 99) if isinstance(_earn_result, dict) else 99
            if _beat > 5 and _days <= 30:
                confidence += 10
                setup_reason += f" | PEAD (+{_beat:.0f}%)"
        except Exception:
            pass

        confidence = min(100, max(0, confidence))

        # BEAR_REGIME_BLOCK with High-Score (>= 80) Bypass
        # [Opposite ETF Cannibalization Guard] 반대 방향 레버리지/인버스 ETF 동시 보유 방지
        # 예: TQQQ(3x Long) 보유 중 SQQQ(3x Short) 동시 매수 금지 (자산 잠식 및 양방향 수수료 낭비 방지)
        opp_map = {
            "SQQQ": {"TQQQ", "QQQ"}, "PSQ": {"TQQQ", "QQQ"},
            "TQQQ": {"SQQQ", "PSQ"}, "QQQ": {"SQQQ", "PSQ"},
            "SOXS": {"SOXL"}, "SOXL": {"SOXS"},
            "SPXU": {"UPRO", "SPY"}, "SH": {"UPRO", "SPY"},
            "UPRO": {"SPXU", "SH"}, "SPY": {"SPXU", "SH"},
        }
        if symbol in opp_map:
            held_symbols = set(self.positions.keys())
            conflicting_held = opp_map[symbol].intersection(held_symbols)
            if conflicting_held:
                return EntrySignal("HOLD", confidence,
                    f"OPPOSITE_CONFLICT_GUARD: Cannot buy {symbol} while holding opposing position {list(conflicting_held)}",
                    current_price)

        if current_regime in _bear_regimes:
            _allowed_in_bear = getattr(config, 'INVERSE_ETFS', set()) | getattr(config, 'DEFENSIVE_UNIVERSE_SET', set())
            if symbol not in _allowed_in_bear:
                if confidence < 70:
                    return EntrySignal("HOLD", confidence, f"BEAR_REGIME_BLOCK: {current_regime} (Score {confidence} < 70)", current_price)
                else:
                    setup_reason += f" | BEAR_BYPASS (Score {confidence} >= 70)"

        # 5. Market Breadth Guard with High-Score (>= 70) Bypass
        try:
            import kis_data
            _spy_df = kis_data.get_daily_ohlcv("SPY", days=25)
            if _spy_df is not None and len(_spy_df) >= 20:
                _spy_close = _spy_df['Close']
                if isinstance(_spy_close, pd.DataFrame):
                    _spy_close = _spy_close.iloc[:, 0]
                _spy_sma20 = float(_spy_close.rolling(20).mean().iloc[-1])
                _spy_current = float(_spy_close.iloc[-1])
                if _spy_current < _spy_sma20 * 0.995:
                    _allowed_in_downtrend = getattr(config, 'INVERSE_ETFS', set()) | getattr(config, 'DEFENSIVE_UNIVERSE_SET', set())
                    if symbol not in _allowed_in_downtrend:
                        if confidence < 70:
                            return EntrySignal("HOLD", confidence, f"BREADTH_GUARD: SPY (${_spy_current:.1f}) below SMA20 (${_spy_sma20:.1f}) (Score {confidence} < 70)", current_price)
                        else:
                            setup_reason += f" | BREADTH_BYPASS (Score {confidence} >= 70)"
        except Exception as e:
            logger.debug("Breadth guard check failed: {}", e)

        if confidence < min_required:
            return EntrySignal("HOLD", confidence, f"Low confidence: {confidence} (needs {min_required})", current_price)

        logger.info(" ENTRY SIGNAL TRIGGERED [v1.0.7]: {} -> BUY (Score: {}, Setup: {})", symbol, confidence, setup_reason)
        return EntrySignal("BUY", confidence, setup_reason, current_price, indicators)


    def _check_entry_filters(self, ind: IndicatorSummary, cfg: PhaseConfig,
                             symbol: str = None, price: float = 0.0) -> dict:
        """Check all entry filters"""
        failed = []
        
        # Inverse ETF exemption for standard long-only overbought & OBV filters
        is_inverse = symbol in getattr(config, 'INVERSE_ETFS', set()) if symbol else False

        # ADX - Trend strength
        if not is_inverse and ind.adx < cfg.min_adx:
            failed.append(f"ADX:{ind.adx:.0f}<{cfg.min_adx}")
        
        # RSI - Not extreme (Exempt inverse ETFs)
        if not is_inverse and (ind.rsi < 30 or ind.rsi > 75):
            failed.append(f"RSI:{ind.rsi:.0f}")
        
        # Bollinger - Not overbought (Exempt inverse ETFs)
        if not is_inverse and ind.bollinger.percent_b > 0.95:
            failed.append(f"BB%:{ind.bollinger.percent_b:.2f}")
        
        # OBV Volume Trend - Require non-down volume trend for non-inverse entries
        obv_tr = getattr(ind, 'obv_trend', 'NEUTRAL')
        if not is_inverse and obv_tr == 'DOWN':
            failed.append("OBV:DOWN")
        if not is_inverse and (not ind.macd.is_bullish and ind.stoch_rsi > 0.7):
            failed.append("MACD_bearish+StochRSI_high")
        
        # OBV trend (Exempt inverse ETFs)
        if not is_inverse and ind.obv_trend == "DOWN":
            failed.append("OBV_down")
        
        # Options: Block entry when pinned at max pain on expiry week
        if symbol and price > 0:
            try:
                if is_near_max_pain(symbol, price, threshold_pct=0.015):
                    failed.append(f"MaxPain_pin({symbol})")
            except Exception:
                pass
        
        return {
            'passed': len(failed) == 0,
            'failed': failed
        }
    
    def _calc_entry_confidence(self, ind: IndicatorSummary, 
                               macro_score: float, cfg: PhaseConfig, df: pd.DataFrame,
                               comp_signal, symbol: str = None) -> int:
        """Calculate entry confidence score ( v2)
        
         30 .       .
        min_entry_score 60~65 , 4    .
        """
        price = float(df['Close'].iloc[-1]) if df is not None and not df.empty else 0.0
        score = 30  # Base score ( 5030)
        
        # ================================
        # Macro contribution (+/- 10)
        # ================================
        if macro_score > 30:
            score += 10
        elif macro_score > 10:
            score += 5
        elif macro_score < -10:
            score -= 5
        
        
        # ================================
        # ADX    (+12)
        # ================================
        if ind.adx > 35:
            score += 12  #   
        elif ind.adx > 28:
            score += 8
        elif ind.adx > cfg.min_adx:
            score += 4
        
        # ================================
        # Regime-Aware Momentum & Reversion
        # ================================
        regime = getattr(self, '_last_regime', 'UNKNOWN')
        is_bull = "BULL" in regime

        if is_bull:
            # --- BULL REGIME: Trend Following & Momentum ---
            if 55 <= ind.rsi <= 75:
                score += 15
            elif 50 <= ind.rsi <= 80:
                score += 8
            elif ind.rsi < 40:
                score -= 5  #   (Oversold)  
                
            if ind.bollinger.percent_b > 0.8:
                score += 12 #   
            elif ind.bollinger.percent_b > 0.5:
                score += 6
            elif ind.bollinger.percent_b < 0.3:
                score -= 5
                
            if ind.macd.cross_up:
                score += 15
            elif ind.macd.is_bullish:
                score += 8
            elif ind.macd.cross_down:
                score -= 5
                
            if ind.stoch_rsi > 0.8:
                score += 8
            elif ind.stoch_rsi > 0.5:
                score += 4
            elif ind.stoch_rsi < 0.2:
                score -= 5

        else:
            # --- BEAR/CHOPPY REGIME: Mean-Reversion & Value ---
            if 40 <= ind.rsi <= 55:
                score += 10
            elif 35 <= ind.rsi <= 60:
                score += 5
            elif ind.rsi > 65:
                score -= 3
            
            if ind.bollinger.percent_b < 0.2:
                score += 10
            elif ind.bollinger.percent_b < 0.4:
                score += 6
            elif ind.bollinger.percent_b > 0.85:
                score -= 5
            
            if ind.macd.cross_up:
                score += 12
            elif ind.macd.is_bullish:
                score += 5
            elif ind.macd.cross_down:
                score -= 5
            
            if ind.stoch_rsi < 0.2:
                score += 8
            elif ind.stoch_rsi < 0.35:
                score += 4
            elif ind.stoch_rsi > 0.85:
                score -= 3
        
        # ================================
        # OBV    (+5)
        # ================================
        if ind.obv_trend == "UP":
            score += 5
        elif ind.obv_trend == "DOWN":
            score -= 3  #  
        
        # ================================
        # Advanced Signal Bonus
        # ================================
        try:
            agg = get_signal_aggregator().analyze(df, symbol=symbol)
            score += agg.bonus_score
        except Exception as e:
            logger.error(f"Signal Aggregator Error: {e}")
            pass
            
        # ================================
        # Master Composite Signal (70 modules) Bonus (+/- 40)
        # ================================
        if comp_signal:
            # composite_score is -100 to 100.
            # Scale to +/- 40 so the 70+ modules can decisively push a borderline stock into a BUY.
            base_bonus = comp_signal.composite_score / 2.5 
            
            # Give a slight boost if agreement confidence is very high (> 80%)
            if comp_signal.confidence > 80 and base_bonus > 0:
                base_bonus *= 1.2
                
            master_bonus = int(base_bonus)
            score += master_bonus
        
        # ================================
        #  Pullback in Uptrend Bonus (+15)
        # ================================
        # If we are in a strong uptrend (SMA20 > SMA50) but price has pulled back (RSI < 45 or BB% < 0.3)
        try:
            sma20 = df['Close'].rolling(20).mean().iloc[-1]
            sma50 = df['Close'].rolling(50).mean().iloc[-1]
            if sma20 > sma50:
                # We are in a structural uptrend
                if ind.rsi < 45:
                    score += 10
                    logger.debug(f"{symbol} Pullback detected: RSI {ind.rsi:.0f} in Uptrend")
                elif ind.bollinger.percent_b < 0.3:
                    score += 8
                    logger.debug(f"{symbol} Pullback detected: BB% {ind.bollinger.percent_b:.2f} in Uptrend")
        except Exception:
            pass

        # ================================
        
        # ================================
        # Options Flow Bonus (+/- 20)
        # Includes: Max Pain, GEX, IV Rank, Sigma Range, Put/Call Ratio
        # ================================
        if symbol:
            try:
                opts_score, opts_reason = get_options_score(symbol, current_price=price)
                score += opts_score
                if opts_score != 0:
                    logger.debug("{} OptionsFlow score: {:+d} | {}", symbol, opts_score, opts_reason)
            except Exception as e:
                logger.debug("Options flow score error for {}: {}", symbol, e)
        
        # ================================
        # VIX Regime Adjustment (+/- 15)
        # ================================
        try:
            vix_snap = get_vix_snapshot()
            score += vix_snap.score_adj
            if abs(vix_snap.score_adj) > 0:
                logger.debug("VIX {} ({:.1f}): score adj {:+d}",
                            vix_snap.regime, vix_snap.vix, vix_snap.score_adj)
        except Exception:
            pass

        # ================================
        # [v2.9.0 ULTRA-FAST REAL-TIME SECTOR & DOW/NASDAQ ATH RADAR]
        # 1. Intraday 15-min Sector Rotation: Recalculated every 15 mins
        # 2. Multi-Index All-Time High (ATH) Detection:
        #    - Dow Jones (DIA) ATH -> Industrials (XLI) & Financials (XLF) +30 pts
        #    - Nasdaq (QQQ) ATH -> Tech (XLK / SMH) & 3x ETFs +30 pts
        #    - Defensive Market -> Staples (XLP) & Pharma (XLV) +35 pts
        # ================================
        dow_leaders = {"CAT", "GE", "BA", "JPM", "GS", "BAC", "UNH", "HON", "MMM", "DIA", "XLI", "XLF"}
        tech_growth_symbols = {
            "NVDA", "AAPL", "MSFT", "AMD", "TSLA", "QQQ", "TQQQ", "SOXL", 
            "GOOGL", "AMZN", "META", "AVGO", "SMH", "XLK", "PLTR", "ARM", "MU", "NFLX", "SOXX"
        }
        defensive_pharma_symbols = {
            "BMY", "GIS", "PEP", "JNJ", "PFE", "MRK", "K", "PG", "KO", "FNB", "CL", "CAG", "CPB", "HSY"
        }
        
        current_regime = getattr(self, '_last_regime', 'BULL_NORMAL')
        is_bear_or_choppy = ("BEAR" in current_regime) or (current_regime in {"CHOPPY", "TRANSITION", "RISK_OFF", "CRASH"})

        # Check Dow Jones & Tech leadership
        if symbol in dow_leaders:
            score += 25
            logger.info("🏛️ [DOW_LEADERSHIP_BOOST] +25 pts added for Dow/Industrial/Financial Leader {}", symbol)
        elif symbol in tech_growth_symbols:
            if not is_bear_or_choppy:
                score += 30
                logger.info("⚡ [BULL_TECH_BOOST] +30 pts added for Tech leader {} during {}", symbol, current_regime)
            else:
                score -= 20
                logger.info("🔻 [BEAR_TECH_PENALTY] -20 pts deducted from Tech leader {} during {}", symbol, current_regime)
        elif symbol in defensive_pharma_symbols:
            if is_bear_or_choppy:
                score += 35
                logger.info("🛡️ [BEAR_DEFENSIVE_BOOST] +35 pts added for Defensive stock {} during {}", symbol, current_regime)
            else:
                score -= 20
                logger.info("⚡ [BULL_DEFENSIVE_PENALTY] -20 pts deducted from Defensive stock {} during {}", symbol, current_regime)

        return min(100, max(0, int(score)))
    
    def check_exit(self, symbol: str, realtime_price: float = None) -> ExitSignal:
        """Comprehensive exit check
        
        Args:
            symbol:  
            realtime_price:   (trader.get_price() )
                           None    Close 
        """
        if symbol not in self._positions:
            return ExitSignal("HOLD", "No position", 0)
        
        pos = self._positions[symbol]
        
        df = self.fetch_data(symbol)
        if df is None:
            return ExitSignal("HOLD", "No data", 0)
        
        # [Quant-Shield] Catastrophic Black-Swan News Exit (파산, 상장폐지 등 실시간 돌발 뉴스 감지 시 강제청산)
        try:
            from news_analyzer import get_news_analyzer
            news_res = get_news_analyzer().analyze(symbol)
            if news_res and getattr(news_res, 'has_catastrophic_risk', False):
                reason = getattr(news_res, 'catastrophic_reason', 'Catastrophic event detected')
                logger.error("🚨 [BLACK_SWAN_SHIELD] CATASTROPHIC RISK DETECTED FOR {}! Reason: {}. Triggering IMMEDIATE EMERGENCY EXIT!", symbol, reason)
                close_price = float(df['Close'].iloc[-1]) if not df.empty else pos.current_price
                return ExitSignal("SELL_ALL", f"EMERGENCY_EXIT - {reason}", close_price)
        except Exception as ex:
            logger.debug("Black-swan news exit check failed: {}", ex)
        
        indicators = analyze_all(df)
        if indicators is None:
            return ExitSignal("HOLD", "Indicator calc failed", 0)
        
        cfg = self.get_phase_config()
        
        #     ( )
        # stop/trailing/TP ,     
        price = realtime_price if realtime_price and realtime_price > 0 else 0
        
        # [Fallback 1] yfinance fast_info (   )
        if price <= 0:
            try:
                import yfinance as _yf
                ticker = _yf.Ticker(symbol)
                price = ticker.fast_info.last_price or 0
                if price > 0:
                    logger.info("yfinance fast_info fallback for {}: ${:.2f}", symbol, price)
            except Exception:
                pass

        # [Fallback 2] kis_data.get_current_price (KIS API  )
        if price <= 0:
            try:
                from kis_data import get_current_price
                price = get_current_price(symbol) or 0
                if price > 0:
                    logger.info("kis_data.get_current_price fallback for {}: ${:.2f}", symbol, price)
            except Exception:
                pass

        # [Fallback 3]         
        if price <= 0:
            price = df['Close'].iloc[-1]
            logger.warning("Price lookup failed for {}. Defaulting to Daily Close: ${:.2f}", symbol, price)
        
        # Update tracking
        old_high = pos.high_since_entry
        pos.high_since_entry = max(pos.high_since_entry, price)
        if pos.high_since_entry != old_high:
            try:
                db_mgr = get_database()
                db_mgr.update_position_tracking(symbol, pos.high_since_entry, pos.stop_price)
            except Exception as e:
                pass
        pnl_pct = (price - pos.entry_price) / pos.entry_price
        
        #  / ETF    (  )
        import config
        is_inverse = symbol in getattr(config, 'INVERSE_ETFS', set())
        is_leveraged = symbol in getattr(config, 'LEVERAGED_ETFS', set())
        
        if is_inverse or is_leveraged:
            hold_days = (datetime.now() - pos.entry_time).days
            
            # []  ETF: 5      (Volatility Decay )
            if is_inverse and hold_days >= 5:
                return ExitSignal("SELL_ALL",
                                f"INVERSE_TIMEOUT: {symbol} held {hold_days} days, forcing exit to avoid decay",
                                price, pnl_pct)

            hold_hours = (datetime.now() - pos.entry_time).total_seconds() / 3600
            
            #  ETF: 24     
            if is_leveraged and hold_hours > getattr(config, 'LEVERAGED_MAX_HOLD_HOURS', 24):
                return ExitSignal("SELL_ALL",
                                f"LEVERAGED_TIMEOUT: {symbol} {hold_hours:.0f}h, P&L {pnl_pct:+.1%}",
                                price, pnl_pct)
            
            #  ETF: 2%  (  )
            if pnl_pct >= config.LEVERAGED_TAKE_PROFIT_PCT:
                return ExitSignal("SELL_ALL",
                                f"LEVERAGED_TP: {pnl_pct:+.1%} >= {config.LEVERAGED_TAKE_PROFIT_PCT:.0%}",
                                price, pnl_pct)
            
            # Leveraged/Inverse ETF Stop Loss: -4.0% threshold (prevents noise whipsaws on 3x leveraged ETFs)
            leveraged_sl_pct = float(getattr(config, 'LEVERAGED_STOP_LOSS_PCT', 0.040))
            if pnl_pct <= -leveraged_sl_pct:
                return ExitSignal("SELL_ALL",
                                f"LEVERAGED_SL: {pnl_pct:+.1%} <= -{leveraged_sl_pct:.1%}",
                                price, pnl_pct)

        # =================================================================
        #     ( )
        # 
        #    (  ): //
        #     (  ): VWAP, , 
        # =================================================================

        # =================================================================
        #  :     (ET 09:30~16:00,  )
        # [BUG FIX v1.0.6]
        # : =, =6.5h (  )
        # :    +  6.5h +   
        # :  15:00    10:00  = 1h() + 0.5h( ) = 1.5h
        # =================================================================
        try:
            from datetime import timedelta
            import pytz as _pytz_hold
            _et_tz = _pytz_hold.timezone('US/Eastern')
            _market_open_time = time(9, 30)
            _market_close_time = time(16, 0)

            _now_raw = datetime.now()
            _entry_raw = pos.entry_time

            # timezone-aware conversion to Eastern Time (ET) naive datetime objects
            if _now_raw.tzinfo is None:
                _now_et = datetime.now(_pytz_hold.utc).astimezone(_et_tz)
            else:
                _now_et = _now_raw.astimezone(_et_tz)
                
            if _entry_raw.tzinfo is None:
                _entry_et = _entry_raw.replace(tzinfo=_pytz_hold.utc).astimezone(_et_tz)
            else:
                _entry_et = _entry_raw.astimezone(_et_tz)
                
            _now_raw = _now_et.replace(tzinfo=None)
            _entry_raw = _entry_et.replace(tzinfo=None)

            is_same_day = (_now_raw.date() == _entry_raw.date())

            if is_same_day:
                #       (shakeout )
                _hold_hours = (_now_raw - _entry_raw).total_seconds() / 3600
                _hold_minutes = _hold_hours * 60
            else:
                # ---      ---
                _hold_hours = 0.0

                # 1)  :   (16:00) 
                _entry_date = _entry_raw.date()
                if _entry_date.weekday() < 5:  # 
                    _entry_time_of_day = _entry_raw.time()
                    _start_t = max(_entry_time_of_day, _market_open_time)
                    _end_t = _market_close_time
                    if _start_t < _end_t:
                        from datetime import date as _date_cls
                        _dummy = _date_cls(2000, 1, 1)
                        _dt_s = datetime.combine(_dummy, _start_t)
                        _dt_e = datetime.combine(_dummy, _end_t)
                        _hold_hours += (_dt_e - _dt_s).total_seconds() / 3600.0

                # 2)   : (+1) ~ (-1)  6.5h
                _curr_date = _entry_raw.date() + timedelta(days=1)
                _today_date = _now_raw.date()
                while _curr_date < _today_date:
                    if _curr_date.weekday() < 5:
                        _hold_hours += 6.5
                    _curr_date += timedelta(days=1)

                # 3)  (): (09:30)  
                if _today_date.weekday() < 5:  # 
                    _now_time_of_day = _now_raw.time()
                    if _now_time_of_day > _market_open_time:
                        from datetime import date as _date_cls2
                        _dummy2 = _date_cls2(2000, 1, 1)
                        _dt_o = datetime.combine(_dummy2, _market_open_time)
                        _dt_n = datetime.combine(_dummy2, min(_now_time_of_day, _market_close_time))
                        _hold_hours += (_dt_n - _dt_o).total_seconds() / 3600.0

                _hold_minutes = _hold_hours * 60
        except Exception as e:
            logger.error("Failed to calculate real hold hours: {}", e)
            _hold_hours = 999
            _hold_minutes = 9990
            is_same_day = False

        # =================================================================
        #  1:     (Emergency Hard Stop Net)
        # =================================================================
        if pnl_pct <= -0.10:
            return ExitSignal("SELL_ALL",
                f"EMERGENCY_STOP: Extreme drawdown {pnl_pct:+.1%} ( {_hold_hours:.1f}h)",
                price, pnl_pct)

        # =================================================================
        #  2:     (Advanced Adaptive Exit Engine)
        # =================================================================
        try:
            # indicators: IndicatorSummary (RSI, ATR, MACD  )
            atr_val = indicators.atr if indicators else 0.0
            
            #      (9:30 ~ 9:45 EST)
            is_early_opening_noise = False
            try:
                et = pytz.timezone('US/Eastern')
                now_et = datetime.now(et)
                if get_market_phase() == MarketPhase.OPENING and now_et.time() < time(9, 45):
                    is_early_opening_noise = True
            except Exception:
                pass

            #    (Shakeout Protection Mode):
            #   15   15   
            #          ' (Breathing Room)' .
            if is_same_day:
                is_shakeout_protection_active = (_hold_minutes < 15) or is_early_opening_noise
            else:
                is_shakeout_protection_active = False

            if is_shakeout_protection_active:
                logger.debug("SHAKEOUT_PROTECTION_ACTIVE for {}: Hold minutes={:.1f}, Early opening={}. Trailing/Reversal exits suspended.",
                             symbol, _hold_minutes, is_early_opening_noise)

            # (1) ATR         (  )
            stop_sig = self._check_stop_loss(pos, price, atr_val, cfg)
            if stop_sig:
                logger.warning(" HARD STOP / ATR STOP TRIGGERED: {} -> {}", symbol, stop_sig.reason)
                return stop_sig

            # (2)   (  +  3%     -1.5%  )
            tp_sig = self._check_take_profit(pos, price, pnl_pct, cfg)
            if tp_sig:
                logger.warning(" TAKE PROFIT / TRAIL LOCK TRIGGERED: {} -> {}", symbol, tp_sig.reason)
                return tp_sig

            #             
            if not is_shakeout_protection_active:
                # (3)      (    )
                trail_sig = self._check_trailing_stop(pos, price, atr_val, cfg)
                if trail_sig:
                    logger.warning(" ADVANCED TRAILING STOP TRIGGERED: {} -> {}", symbol, trail_sig.reason)
                    return trail_sig

                # (4)     (MACD , Bollinger/StochRSI   )
                reversal_sig = self._check_reversal_signals(pos, indicators, price)
                if reversal_sig:
                    logger.warning(" REVERSAL EXIT TRIGGERED: {} -> {}", symbol, reversal_sig.reason)
                    return reversal_sig

        except Exception as exit_e:
            logger.error("Advanced Adaptive Exit Engine error for {}: {}", symbol, exit_e)

        # [Overnight Gap Risk Shield] 3x 레버리지/인버스 ETF 장 마감 15분 전(EST 15:45) 전량 자동 청산
        # 밤 사이 시장 휴장 시간에 발생하는 갭하락 폭락 위험을 100% 원천 차단함
        is_lev_or_inv = (symbol in getattr(config, 'INVERSE_ETFS', set())) or (symbol in getattr(config, 'LEVERAGED_ETFS', set()))
        if is_lev_or_inv and getattr(config, 'OVERNIGHT_LEVERAGE_EXIT', False):
            try:
                et = pytz.timezone('US/Eastern')
                now_et = datetime.now(et)
                # EST 15:45 (장 마감 15분 전) 이후 3x 레버리지/인버스 ETF 오버나이트 금지 청산
                if now_et.time() >= time(15, 45):
                    return ExitSignal("SELL_ALL",
                        f"OVERNIGHT_GAP_SHIELD: Closing {symbol} before market close to 100% prevent overnight gap-down risk (P&L: {pnl_pct:+.1%})",
                        price, pnl_pct)
            except Exception as _e_gap:
                logger.debug("Overnight gap shield check error: {}", _e_gap)

        # [Inverse ETF Timeout] 5일 보유 시 변동성 잠식(Decay) 방지 청산
        if symbol in getattr(config, 'INVERSE_ETFS', set()):
            if _hold_hours >= 32.5:
                return ExitSignal("SELL_ALL",
                    f"INVERSE_TIMEOUT: {_hold_hours/6.5:.1f} days held, forcing exit to prevent decay",
                    price, pnl_pct)

        # 
        # [  ]   5 (32.5h)   15:30 
        #     (  )
        # 
        if _hold_hours >= 32.5:
            try:
                et = pytz.timezone('US/Eastern')
                now_et = datetime.now(et)
                #  15:30     
                if now_et.weekday() == 4 and now_et.time() >= time(15, 30):
                    return ExitSignal("SELL_ALL",
                        f"SWING_WEEKLY_EXIT: {_hold_hours/6.5:.1f}     ({pnl_pct:+.1%})",
                        price, pnl_pct)
                #   7 (45.5h)     (  )
                if _hold_hours >= 45.5:
                    return ExitSignal("SELL_ALL",
                        f"MAX_HOLD: {_hold_hours/6.5:.1f} ,   ({pnl_pct:+.1%})",
                        price, pnl_pct)
            except Exception:
                pass

        return ExitSignal("HOLD", f"SWING_HOLD: {pnl_pct:+.1%} ({_hold_hours:.0f}h)", price, pnl_pct)

    def _check_stop_loss(self, pos: Position, price: float, 
                         atr: float, cfg: PhaseConfig) -> Optional[ExitSignal]:
        """ATR-based stop loss with regime-aware hard fallback"""
        pnl_pct = (price - pos.entry_price) / pos.entry_price
        current_regime = getattr(self, '_last_regime', '')
        bear_regimes = {"BEAR_NORMAL", "BEAR_TRENDING", "BEAR_VOLATILE", "BEAR_PANIC"}
        choppy_regimes = {"CHOPPY", "TRANSITION", "CHOPPY_VOLATILE", "RANGE_BOUND"}
        stop_mult = getattr(cfg, 'stop_loss_atr', 1.5)
        
        # Scale stop multiplier based on regime
        if current_regime in bear_regimes:
            stop_mult *= 0.90   # Tighter ATR stop in bear markets
        elif current_regime in choppy_regimes:
            stop_mult *= 1.25   # Wider ATR stop to absorb chop whipsaws
        elif "BULL" in current_regime:
            stop_mult *= 0.85   # Tighter ATR stop in clean bull trends

        # ATR-based stop
        if pos.atr_at_entry > 0:
            stop_price = pos.entry_price - (pos.atr_at_entry * stop_mult)
        else:
            stop_price = pos.entry_price * 0.95
            
        # Regime-aware hard stop:
        # [CRITICAL FIX] config.py에 정의된 손절률(7%)을 강제로 존중하도록 연동. 
        # 이전에는 config에서 7%로 늘렸으나 내부 하드코딩 5%/4%에 막혀 오동작 중이었음.
        if current_regime in bear_regimes:
            hard_stop_pct = float(getattr(config, 'BEAR_HARD_STOP_PCT', 0.07))
        else:
            hard_stop_pct = float(getattr(config, 'STOP_LOSS_PCT', 0.07))
        
        hard_stop_price = pos.entry_price * (1 - hard_stop_pct)
        effective_stop = max(stop_price, hard_stop_price)
        
        # Break-even stop for scale-out position
        if pos.half_sold:
            effective_stop = max(effective_stop, pos.entry_price * 1.005)
        
        if price <= effective_stop:
            reason = f"STOP: ${price:.2f} <= ${effective_stop:.2f} (ATR={pos.atr_at_entry:.2f})"
            if effective_stop == hard_stop_price:
                reason = f"HARD_STOP: P&L {pnl_pct:+.1%} <= -{hard_stop_pct:.0%}"
                
            return ExitSignal("SELL_ALL", reason, price, pnl_pct)
            
        # ── [QUANT ENGINE] 전면적 시장 패닉(Systemic Panic) vs 섹터 순환매(Sector Rotation) 정밀 구분 ──
        # 1) 전면적 시장 패닉(BEAR_PANIC / VIX > 28): 시장 전체 폭락 시에만 기술주 롱 포지션 강제 현금화
        # 2) 섹터 순환매(BEAR_NORMAL / Sector Shift): 기술주에서 방어주/가치주로 자금이 이동하는 순환매 장세에서는
        #    무조건 강제 청산하지 않고, 개별 종목의 손절가/익절가/트레일링스탑 지표에 따라서만 정밀 매도 수행!
        panic_bear_regimes = {"BEAR_PANIC", "CRASH", "SYSTEMIC_RISK"}
        _allowed_in_bear = getattr(config, 'INVERSE_ETFS', set()) | getattr(config, 'DEFENSIVE_UNIVERSE_SET', set())
        
        if current_regime in panic_bear_regimes:
            # 전면적 시장 폭락 패닉 시에만 방어주가 아닌 손실 포지션 현금화
            if pnl_pct < 0 and pos.symbol not in _allowed_in_bear:
                reason = f"SYSTEMIC_PANIC_EXIT: Market in {current_regime}. Securing capital for crash protection."
                logger.warning("🚨 [PANIC_GUARD] Force exiting position {} during broad crash | Reason: {}", pos.symbol, reason)
                return ExitSignal("SELL_ALL", reason, price, pnl_pct)
        elif current_regime in bear_regimes:
            # 단순 약세/섹터 순환매 장세에서는 강제 매도하지 않고 순환매 수급 및 트레일링 스탑에만 의존함
            logger.debug("SECTOR_ROTATION_MODE: Holding {} during {} (SL/TP/Trailing active)", pos.symbol, current_regime)

        return None

    
    def _check_trailing_stop(self, pos: Position, price: float,
                            atr: float, cfg: PhaseConfig) -> Optional[ExitSignal]:
        """Trailing stop based on high since entry with dynamic tightening"""
        if pos.high_since_entry <= pos.entry_price:
            return None
            
        pnl_pct_high = (pos.high_since_entry - pos.entry_price) / pos.entry_price
        
        # Exponential Chandelier Hook 
        dynamic_atr_mult = cfg.trailing_atr
        breakeven_hook = False
        
        if pnl_pct_high > 0.10:
            dynamic_atr_mult = min(dynamic_atr_mult, 0.2)
        elif pnl_pct_high > 0.06:
            dynamic_atr_mult = min(dynamic_atr_mult, 0.4)
            breakeven_hook = True
        elif pnl_pct_high > 0.03:
            dynamic_atr_mult = min(dynamic_atr_mult, 0.8)
            
        trailing_stop = pos.high_since_entry - (atr * dynamic_atr_mult)
        
        # Wall Street SOTA Profit Lock Escalator:
        # Guarantee Zero-Loss / Lock Profits dynamically as price rises
        if pnl_pct_high >= 0.08:
            trailing_stop = max(trailing_stop, pos.entry_price * 1.050)  # Lock +5.0% profit minimum
        elif pnl_pct_high >= 0.05:
            trailing_stop = max(trailing_stop, pos.entry_price * 1.025)  # Lock +2.5% profit minimum
        elif pnl_pct_high >= 0.025:
            trailing_stop = max(trailing_stop, pos.entry_price * 1.005)  # Lock +0.5% profit (Risk-Free Trade)
        
        # Absolute Hook: If we were 6% up, trailing stop CANNOT go below Entry + 1%.
        if breakeven_hook:
            trailing_stop = max(trailing_stop, pos.entry_price * 1.01)
        
        if price <= trailing_stop:
            pnl_pct = (price - pos.entry_price) / pos.entry_price
            return ExitSignal("SELL_ALL",
                            f"TRAIL(SOTA_LOCK): ${price:.2f} <= ${trailing_stop:.2f} (High P&L: {pnl_pct_high:+.1%})",
                            price, pnl_pct)
        return None
    
    def _check_take_profit(self, pos: Position, price: float,
                          pnl_pct: float, cfg: PhaseConfig) -> Optional[ExitSignal]:
        """Take profit check with Scale-Out (1.5R half-sell, 3.0R final sell) and regime scaling"""
        current_regime = getattr(self, '_last_regime', '')
        bear_regimes = {"BEAR_NORMAL", "BEAR_TRENDING", "BEAR_VOLATILE", "BEAR_PANIC"}
        choppy_regimes = {"CHOPPY", "TRANSITION", "CHOPPY_VOLATILE", "RANGE_BOUND"}
        tp_pct = cfg.take_profit_pct
        tp_mult = 1.0
        
        if current_regime in bear_regimes:
            tp_mult = 0.65       # Fast cash-outs in bear markets
        elif current_regime in choppy_regimes:
            tp_mult = 0.75       # Fast cash-outs in choppy ranges
        elif "BULL" in current_regime:
            tp_mult = 1.40       # Let winners run in bull trends!
            
        tp_pct *= tp_mult

        # 1R Risk (Distance to stop loss) calculation
        entry_stop_price = getattr(pos, 'stop_price', pos.entry_price * 0.95)
        risk_1r = pos.entry_price - entry_stop_price
        if risk_1r <= 0:
            risk_1r = pos.entry_price * 0.05
            
        # Scale risk based on regime multiplier
        scaled_risk_1r = risk_1r * tp_mult
        
        # 1.5R and 3.0R targets
        target_15r = pos.entry_price + (1.5 * scaled_risk_1r)
        target_30r = pos.entry_price + (3.0 * scaled_risk_1r)
        
        # [ATR-Adaptive TP] Min/Max TP derived from each stock's own volatility at entry
        # High-vol stocks (ATR 5%+) get higher TP targets; low-vol stocks (ATR 1-2%) get lower targets
        max_tp_pct = 0.22  # Hard cap: never target >22% (take money and run)
        atr_at_entry = getattr(pos, 'atr_at_entry', 0.0)
        if atr_at_entry > 0.0 and pos.entry_price > 0.0:
            atr_pct = atr_at_entry / pos.entry_price
            # Min TP = 1.5x ATR: meaningful target relative to the stock's natural daily range
            # Floor at 2% (avoid noise), cap at 12% (stay realistic for swing trades)
            min_tp_pct = max(0.02, min(0.12, 1.5 * atr_pct))
        else:
            min_tp_pct = 0.04  # Fallback if ATR not stored
        target_30r_pct = (target_30r - pos.entry_price) / pos.entry_price if pos.entry_price > 0 else 0
        
        if target_30r_pct > max_tp_pct:
            target_30r = pos.entry_price * (1.0 + max_tp_pct)
            target_15r = pos.entry_price + (target_30r - pos.entry_price) * 0.5
            logger.debug("[DYNAMIC_TP] Clamped 30R for {} {:.1%} → max {:.1%}", pos.symbol, target_30r_pct, max_tp_pct)
        elif target_30r_pct < min_tp_pct:
            target_30r = pos.entry_price * (1.0 + min_tp_pct)
            target_15r = pos.entry_price + (target_30r - pos.entry_price) * 0.5
            atr_pct_log = (atr_at_entry / pos.entry_price) if atr_at_entry > 0 and pos.entry_price > 0 else 0
            logger.debug("[ATR_TP] {} | ATR={:.1%} → MinTP={:.1%} (raw 30R was {:.1%})", pos.symbol, atr_pct_log, min_tp_pct, target_30r_pct)
            
        # Scale-Out TP Exits (50% 분할 익절 및 100% 무위험 거래 전환)
        # 고정 %가 아닌 각 종목 고유의 변동성(ATR 1.5R) 타겟에 도달 시 1차 분할 익절 실행
        if not pos.half_sold:
            if price >= target_15r:
                t15r_pct = (target_15r - pos.entry_price) / pos.entry_price if pos.entry_price > 0 else 0
                return ExitSignal("SELL_HALF",
                                f"SCALE_OUT_50%: {pnl_pct:+.1%} >= 1.5R ATR target (${target_15r:.2f}, +{t15r_pct:.1%})",
                                price, pnl_pct)
        else:
            final_target_r = 4.5 if "BULL" in current_regime else 3.0
            target_final = pos.entry_price + (final_target_r * scaled_risk_1r)
            if price >= target_final:
                return ExitSignal("SELL_ALL",
                                f"FINAL_TP_{final_target_r:.1f}R: {pnl_pct:+.1%} >= {final_target_r:.1f}R target (${target_final:.2f})",
                                price, pnl_pct)
        
        # Dynamic Trailing profit lock: Once up, trail from peak (lock in gains)
        trail_activate = config.TRAILING_TRIGGER_PCT
        trail_dist = config.TRAILING_STOP_PCT
        
        if "BULL" in current_regime:
            # Let winners run: raise activation trigger and widen trailing distance
            trail_activate *= 1.33
            trail_dist *= 1.33
        elif current_regime in bear_regimes or current_regime in choppy_regimes:
            # Lock in profits quickly: lower activation trigger and tighten trailing distance
            trail_activate *= 0.67
            trail_dist *= 0.67
            
        if pos.high_since_entry > 0:
            peak_pnl = (pos.high_since_entry - pos.entry_price) / pos.entry_price
            if peak_pnl >= trail_activate:
                trailing_lock = pos.high_since_entry * (1 - trail_dist)
                if price <= trailing_lock:
                    return ExitSignal("SELL_ALL",
                                    f"DYNAMIC_TRAIL_LOCK: peak +{peak_pnl:.1%}, locked at ${trailing_lock:.2f} (P&L {pnl_pct:+.1%})",
                                    price, pnl_pct)
        
        return None
    
    def _check_reversal_signals(self, pos: Position, ind: IndicatorSummary,
                               price: float) -> Optional[ExitSignal]:
        """Check for reversal indicators"""
        pnl_pct = (price - pos.entry_price) / pos.entry_price
        
        # MACD bearish cross
        if ind.macd.cross_down and pnl_pct >= 0.03:
            return ExitSignal("SELL_ALL", "MACD bearish cross", price, pnl_pct)
        
        # Extreme overbought — only exit if we actually have profit to protect
        # [v1.1.8] Added pnl_pct > 0.01: previously selling at BB%=1.05 even at breakeven (avg +0.02%)
        if ind.bollinger.percent_b > 1.05 and ind.rsi > 75 and pnl_pct > 0.01:
            return ExitSignal("SELL_ALL", 
                            f"Overbought: BB%={ind.bollinger.percent_b:.2f}, RSI={ind.rsi:.0f}",
                            price, pnl_pct)
        
        # Stochastic RSI extreme + profit (Require MACD cross_down & RSI > 78 to prevent cutting winners prematurely)
        if ind.stoch_rsi > 0.95 and ind.rsi > 78 and ind.macd.cross_down and pnl_pct > 0.06:
            return ExitSignal("SELL_ALL", f"StochRSI+MACD Bearish Reversal: RSI={ind.rsi:.0f}, Stoch={ind.stoch_rsi:.2f}",
                            price, pnl_pct)
        
        return None
    
    # ==============================================
    # Position Management
    # ==============================================
    
    def add_position(self, symbol: str, entry_price: float, 
                    quantity: int, atr: float):
        """Add new position"""
        cfg = self.get_phase_config()
        
        # 🎯 테마 레이더의 변동성 기반 동적 손절가(stop_loss) 적용 시도
        stop_price = None
        try:
            from theme_radar_adapter import ThemeRadarAdapter
            adapter = ThemeRadarAdapter()
            recs = adapter.get_recommendations()
            if symbol in recs:
                stop_pct = recs[symbol]["stop_pct"]
                stop_price = entry_price * (1 - stop_pct / 100)
                logger.info("🎯 [THEME_RADAR_STOP] Applied dynamic stop-loss for {}: {}% (${:.2f})", 
                            symbol, stop_pct, stop_price)
        except Exception as e:
            logger.debug("Failed to fetch Theme Radar stop loss: {}", e)

        # Fallback to standard ATR stop if not matched in Theme Radar
        if stop_price is None:
            stop_price = entry_price - (atr * cfg.stop_loss_atr) if atr > 0 else entry_price * 0.95
        
        self._positions[symbol] = Position(
            symbol=symbol,
            entry_price=entry_price,
            quantity=quantity,
            entry_time=datetime.now(),
            atr_at_entry=atr,
            high_since_entry=entry_price,
            stop_price=stop_price,
            trailing_stop=entry_price,
            phase_at_entry=get_market_phase()
        )
        try:
            db_mgr = get_database()
            db_mgr.update_position_tracking(symbol, entry_price, stop_price)
        except Exception as e:
            pass
        logger.info("Position added: {} @ ${:.2f}, stop ${:.2f}", 
                   symbol, entry_price, stop_price)
    
    def mark_half_sold(self, symbol: str):
        if symbol in self._positions:
            self._positions[symbol].half_sold = True
            self._positions[symbol].quantity //= 2
    
    def remove_position(self, symbol: str):
        if symbol in self._positions:
            del self._positions[symbol]
    
    def sync_positions(self, api_positions: list):
        """
        KIS API  strategy  
        
              :
        -   
        - /  
        -      (  )
        """
        synced = 0
        from database import get_database
        db_mgr = None
        try:
            db_mgr = get_database()
        except Exception as e:
            logger.error("Failed to initialize database connection: {}", e)
            
        for pos in api_positions:
            symbol = pos.symbol
            if db_mgr:
                try:
                    db_mgr.update_position(symbol, pos.quantity, pos.avg_price)
                except Exception as de:
                    logger.debug("Database update failed during sync for {}: {}", symbol, de)
                    
            if symbol not in self._positions:
                # Retrieve true entry state if possible
                true_entry_time = datetime.now()
                true_high = max(pos.avg_price, pos.current_price)
                stop_price = None
                
                if db_mgr:
                    try:
                        # Find entry time and tracking states from database
                        open_positions = db_mgr.get_open_positions()
                        matching = [p for p in open_positions if p['symbol'] == symbol]
                        if matching:
                            db_pos = matching[0]
                            
                            # Recover entry time
                            db_entry_time = db_pos.get('entry_time')
                            if isinstance(db_entry_time, str):
                                try:
                                    db_entry_time = datetime.fromisoformat(db_entry_time)
                                except Exception as e:
                                    logger.error("Failed to parse DB entry time string '{}': {}", db_entry_time, e)
                            if isinstance(db_entry_time, datetime):
                                true_entry_time = db_entry_time
                                logger.info("Recovered true entry time for {}: {}", symbol, true_entry_time)
                                
                            # Recover tracking values (high_since_entry, stop_price) to prevent state loss on restart
                            db_high = db_pos.get('high_since_entry', 0.0)
                            db_stop = db_pos.get('stop_price', 0.0)
                            if db_high and db_high > pos.avg_price * 0.5:
                                true_high = max(true_high, db_high)
                                logger.info("Recovered true high since entry for {}: ${:.2f}", symbol, true_high)
                            if db_stop and db_stop > pos.avg_price * 0.5:
                                stop_price = db_stop
                                logger.info("Recovered stop price from DB for {}: ${:.2f}", symbol, stop_price)
                    except Exception as e:
                        logger.debug("Could not query true entry state for {}: {}", symbol, e)

                # ATR  
                df = self.fetch_data(symbol)
                atr = 0.0
                if df is not None and len(df) >= 14:
                    from indicators import calculate_atr
                    atr_series = calculate_atr(df)
                    atr = float(atr_series.iloc[-1]) if len(atr_series) > 0 else 0.0
                
                cfg = self.get_phase_config()
                if stop_price is None:
                    stop_price = pos.avg_price - (atr * cfg.stop_loss_atr) if atr > 0 else pos.avg_price * 0.95
                
                self._positions[symbol] = Position(
                    symbol=symbol,
                    entry_price=pos.avg_price,
                    quantity=pos.quantity,
                    entry_time=true_entry_time,
                    atr_at_entry=atr,
                    high_since_entry=true_high,
                    stop_price=stop_price,
                    trailing_stop=pos.avg_price,
                    phase_at_entry=get_market_phase()
                )
                synced += 1
                logger.info("Synced position: {} x {} @ ${:.2f} (stop ${:.2f})",
                           symbol, pos.quantity, pos.avg_price, stop_price)
        
        #     (  )
        api_symbols = {p.symbol for p in api_positions}
        stale = [s for s in self._positions if s not in api_symbols]
        for s in stale:
            logger.warning("Removing stale position: {}", s)
            del self._positions[s]
            
            #   (  0 )
            if db_mgr:
                try:
                    db_mgr.update_position(s, 0, 0)
                    logger.info("  -> Database updated: {} zeroed out", s)
                except Exception as de:
                    logger.debug("  -> Database update failed for {}: {}", s, de)
        
        logger.info("Position sync complete: {} synced, {} removed", synced, len(stale))
    
    def get_position(self, symbol: str) -> Optional[Position]:
        return self._positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, Position]:
        return self._positions.copy()
    
    def get_current_atr(self, symbol: str) -> float:
        if symbol in self._data_cache:
            df = self._data_cache[symbol]
            return calculate_atr(df).iloc[-1]
        return 0.0


# Global instance
_strategy = None

def get_strategy() -> StrategyEngine:
    global _strategy
    if _strategy is None:
        _strategy = StrategyEngine()
    return _strategy


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="DEBUG", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing Enhanced Strategy Engine...")
    
    phase = get_market_phase()
    cfg = PHASE_CONFIGS.get(phase, PHASE_CONFIGS[MarketPhase.MIDDAY])
    
    print(f"\nPhase: {phase.value}")
    print(f"Config: {cfg.description}")
    print(f"  TP: {cfg.take_profit_pct:.0%}, SL: {cfg.stop_loss_atr}x ATR")
    print(f"  Min ADX: {cfg.min_adx}, Min Score: {cfg.min_entry_score}")
    
    engine = StrategyEngine()
    
    # Test entry
    signal = engine.check_entry("AMD", macro_score=30)
    print(f"\nAMD Entry Signal:")
    print(f"  Action: {signal.action}")
    print(f"  Confidence: {signal.confidence}")
    print(f"  Reason: {signal.reason}")
    
    if signal.indicators:
        ind = signal.indicators
        print(f"\n  Indicators:")
        print(f"    ADX: {ind.adx:.1f} ({ind.trend_strength})")
        print(f"    RSI: {ind.rsi:.1f}")
        print(f"    MACD: {'Bullish' if ind.macd.is_bullish else 'Bearish'}")
        print(f"    BB%: {ind.bollinger.percent_b:.2f}")
        print(f"    StochRSI: {ind.stoch_rsi:.2f}")
