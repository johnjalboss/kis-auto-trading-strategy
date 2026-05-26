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
            trailing_atr=atr_mult * 1.3,  # 0.8 → 1.3: 이익 더 길게 유지
            position_mult=0.8,            # 0.5 → 0.8: 장중 신호에도 충분한 비중
            min_adx=25,
            min_entry_score=70,
            description="Conservative midday"
        ),
        MarketPhase.CLOSING: PhaseConfig(
            take_profit_pct=tp_base * 1.2,
            stop_loss_atr=atr_mult,
            trailing_atr=atr_mult * 1.1,  # 0.8 → 1.1: 마감 시간대에도 움직임 허용
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
    except:
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
    
    def fetch_data(self, symbol: str, period: str = "3mo",
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
        PURE SWING TRADING ENTRY LOGIC
        """
        if symbol in self._positions:
            return EntrySignal("HOLD", 0, "Already in position", 0)
        
        if macro_score < -20:
            return EntrySignal("HOLD", 0, f"Macro too risky: {macro_score:.0f}", 0)
        
        try:
            vix_snap = get_vix_snapshot()
            if vix_snap.regime == "EXTREME":
                return EntrySignal("HOLD", 0, f"VIX extreme ({vix_snap.vix:.1f})  market crash mode", 0)
        except Exception:
            pass

        _bear_regimes = {"BEAR_NORMAL", "BEAR_TRENDING", "BEAR_VOLATILE"}
        _choppy_regimes = {"CHOPPY", "TRANSITION", "CHOPPY_VOLATILE"}
        current_regime = getattr(self, '_last_regime', '')

        # CHOPPY/TRANSITION 레짐: 방향성이 없어 승률 저하 → 진입 차단
        if current_regime in _choppy_regimes:
            logger.debug("CHOPPY_REGIME_BLOCK: {} — {} 레짐에서 신규 진입 차단", symbol, current_regime)
            return EntrySignal("HOLD", 0, f"CHOPPY_REGIME_BLOCK: {current_regime} — 방향성 없음", 0)

        if current_regime in _bear_regimes:
            _allowed_in_bear = getattr(config, 'INVERSE_ETFS', set()) | getattr(config, 'DEFENSIVE_UNIVERSE_SET', set())
            if symbol not in _allowed_in_bear:
                return EntrySignal("HOLD", 0, f"BEAR_REGIME_BLOCK: {current_regime}  only inverse/defensive allowed", 0)

        #  EARNINGS GUARD
        try:
            from earnings_calendar import get_earnings_calendar
            ec = get_earnings_calendar()
            e_info = ec.check(symbol)
            if e_info.recommendation == "AVOID":
                return EntrySignal("HOLD", 0, f"EARNINGS_GUARD: {symbol}  {e_info.days_until}    ", 0)
        except Exception:
            pass

        #  ECON GUARD
        try:
            from economic_calendar import get_economic_calendar
            econ_cal = get_economic_calendar()
            today_events = econ_cal.get_todays_events() if hasattr(econ_cal, 'get_todays_events') else []
            high_impact = [e for e in today_events if getattr(e, 'impact', '') == 'HIGH']
            if high_impact:
                return EntrySignal("HOLD", 0, f"ECON_EVENT_GUARD:      ", 0)
        except Exception:
            pass

        #  INSIDER GUARD
        try:
            from insider_tracker import get_insider_tracker
            insider = get_insider_tracker()
            ins_result = insider.analyze(symbol)
            if ins_result.insider_net_value < -5_000_000 and ins_result.insider_sentiment == "SELLING":
                return EntrySignal("HOLD", 0, f"INSIDER_GUARD:      ", 0)
        except Exception:
            pass

        #  BREADTH GUARD
        try:
            import kis_data as _kd
            _spy_df = _kd.get_daily_ohlcv("SPY", days=25)
            if _spy_df is not None and len(_spy_df) >= 22:
                _spy_close = _spy_df['Close']
                _spy_sma20 = float(_spy_close.rolling(20).mean().iloc[-1])
                _spy_current = float(_spy_close.iloc[-1])
                if _spy_current < _spy_sma20 * 0.995:
                    if symbol not in getattr(config, 'INVERSE_ETFS', set()):
                        return EntrySignal("HOLD", 0, f"BREADTH_GUARD: SPY ${_spy_current:.1f} < SMA20 ${_spy_sma20:.1f}", 0)
        except Exception:
            pass

        df_daily = self.fetch_data(symbol)
        if df_daily is None or len(df_daily) < 50:
            return EntrySignal("HOLD", 0, "Insufficient daily data for Swing", 0)

        current_price = float(df_daily['Close'].iloc[-1])
        
        # ============================================================
        # 🚨 장초반 변동성 관리: MORNING SPIKE & FADE / GAP & CRAP GUARDS
        # ============================================================
        phase = get_market_phase()
        if phase == MarketPhase.OPENING:
            try:
                open_today = float(df_daily['Open'].iloc[-1])
                high_today = float(df_daily['High'].iloc[-1])
                low_today = float(df_daily['Low'].iloc[-1])
                
                # 1. MORNING GAP & CRAP GUARD: 시가 대비 하락세인 경우 진입 금지 (음봉)
                if current_price < open_today:
                    logger.warning("MORNING_GAP_AND_CRAP_GUARD: {} 시가 미만 감지 (시가: ${:.2f}, 현재가: ${:.2f})", 
                                   symbol, open_today, current_price)
                    return EntrySignal("HOLD", 0, f"MORNING_GAP_AND_CRAP_GUARD: Trading below daily open (${open_today:.2f})", current_price)
                
                # 2. MORNING FADE GUARD: 장초반 급상승 후 40% 이상 흘러내린 경우 진입 금지 (Bull Trap)
                daily_range = high_today - open_today
                if daily_range > 0:
                    fade_ratio = (high_today - current_price) / daily_range
                    if fade_ratio > 0.40:
                        logger.warning("MORNING_FADE_GUARD: {} 고점 대비 {:.1f}% 되돌림 감지 (시가: ${:.2f}, 고가: ${:.2f}, 현재가: ${:.2f})", 
                                       symbol, fade_ratio * 100, open_today, high_today, current_price)
                        return EntrySignal("HOLD", 0, f"MORNING_FADE_GUARD: Retraced {fade_ratio:.0%} of morning gain", current_price)
                
                # 3. VOLATILITY SHAKEOUT GUARD: 시가 대비 -2% 이상 급락세 차단
                if current_price < open_today * 0.98:
                    logger.warning("VOLATILITY_SHAKEOUT_GUARD: {} 시가 대비 -2% 초과 급락 (시가: ${:.2f}, 현재가: ${:.2f})",
                                   symbol, open_today, current_price)
                    return EntrySignal("HOLD", 0, f"VOLATILITY_SHAKEOUT_GUARD: Panic drop below open", current_price)
            except Exception as e:
                logger.debug("Morning volatility guard evaluation failed for {}: {}", symbol, e)
        # ============================================================
        sma20 = df_daily['Close'].rolling(20).mean().iloc[-1]
        sma50 = df_daily['Close'].rolling(50).mean().iloc[-1]
        structural_uptrend = sma20 > sma50

        from indicators import calculate_rsi, calculate_macd
        rsi_val = float(calculate_rsi(df_daily).iloc[-1])
        
        confidence = 60
        reason = "SWING_BASE"

        # VCP / Breakout Check
        _52w_high = float(df_daily['High'].tail(252).max()) if len(df_daily) >= 252 else float(df_daily['High'].max())
        _pct_from_high = (current_price - _52w_high) / _52w_high
        
        is_breakout = _pct_from_high >= -0.02
        is_pullback = structural_uptrend and (40 <= rsi_val <= 65) and (current_price > sma50)
        
        if is_breakout:
            confidence += 25
            reason = "SWING_BREAKOUT: 52W High Proximity"
        elif is_pullback:
            confidence += 15
            reason = f"SWING_PULLBACK: RSI {rsi_val:.1f}, Trend UP"
        else:
            return EntrySignal("HOLD", 0, "No Swing Setup (Not a Breakout or Pullback)", current_price)

        # Volume confirmation
        vol_recent = float(df_daily['Volume'].iloc[-1])
        vol_avg = float(df_daily['Volume'].iloc[:-1].mean())
        if vol_avg > 0 and vol_recent > vol_avg * 1.5:
            confidence += 10
            
        # PEAD Bonus
        try:
            from earnings_analyzer import get_earnings_analyzer
            _ea = get_earnings_analyzer()
            _earn_result = _ea.analyze(symbol)
            _beat = (_earn_result.get('beat_surprise', 0) or _earn_result.get('eps_surprise_pct', 0)) if isinstance(_earn_result, dict) else 0
            _days = _earn_result.get('days_since_earnings', 99) if isinstance(_earn_result, dict) else 99
            if _beat > 5 and _days <= 30:
                confidence += 15
                reason += f" | PEAD (+{_beat:.0f}%)"
        except Exception:
            pass

        confidence = min(100, max(0, confidence))
        cfg = self.get_phase_config()
        min_required = config.SCREENED_MIN_SCORE if is_screened else cfg.min_entry_score
        
        if confidence < min_required:
            return EntrySignal("HOLD", confidence, f"Low confidence: {confidence} (needs {min_required})", current_price)

        return EntrySignal("BUY", confidence, reason, current_price)


    def _check_entry_filters(self, ind: IndicatorSummary, cfg: PhaseConfig,
                             symbol: str = None, price: float = 0.0) -> dict:
        """Check all entry filters"""
        failed = []
        
        # ADX - Trend strength
        if ind.adx < cfg.min_adx:
            failed.append(f"ADX:{ind.adx:.0f}<{cfg.min_adx}")
        
        # RSI - Not extreme
        if ind.rsi < 30 or ind.rsi > 75:
            failed.append(f"RSI:{ind.rsi:.0f}")
        
        # Bollinger - Not overbought
        if ind.bollinger.percent_b > 0.95:
            failed.append(f"BB%:{ind.bollinger.percent_b:.2f}")
        
        # MACD or Stochastic RSI must be favorable
        if not ind.macd.is_bullish and ind.stoch_rsi > 0.7:
            failed.append("MACD_bearish+StochRSI_high")
        
        # OBV trend
        if ind.obv_trend == "DOWN":
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
        pos.high_since_entry = max(pos.high_since_entry, price)
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
            
            #  ETF: 1.5%  ()
            if pnl_pct <= -0.015:
                return ExitSignal("SELL_ALL",
                                f"LEVERAGED_SL: {pnl_pct:+.1%} <= -1.5%",
                                price, pnl_pct)

        # =================================================================
        #     ( )
        # 
        #    (  ): //
        #     (  ): VWAP, , 
        # =================================================================

        #    (    )
        try:
            _hold_hours = (datetime.now() - pos.entry_time).total_seconds() / 3600
        except Exception:
            _hold_hours = 999  # entry_time     

        # =================================================================
        # 🛡️ 1단계: 최우선 비상 서킷 브레이커 (Emergency Hard Stop Net)
        # =================================================================
        if pnl_pct <= -0.10:
            return ExitSignal("SELL_ALL",
                f"EMERGENCY_STOP: Extreme drawdown {pnl_pct:+.1%} ( {_hold_hours:.1f}h)",
                price, pnl_pct)

        # =================================================================
        # 🛡️ 2단계: 최첨단 다이내믹 탈출 엔진 (Advanced Adaptive Exit Engine)
        # =================================================================
        try:
            # indicators: IndicatorSummary (RSI, ATR, MACD 등 포함)
            atr_val = indicators.atr if indicators else 0.0
            
            # 보유 분 단위 계산
            _hold_minutes = _hold_hours * 60
            
            # 장초반 극심한 변동성 시간대 여부 (9:30 ~ 9:45 EST)
            is_early_opening_noise = False
            try:
                et = pytz.timezone('US/Eastern')
                now_et = datetime.now(et)
                if get_market_phase() == MarketPhase.OPENING and now_et.time() < time(9, 45):
                    is_early_opening_noise = True
            except Exception:
                pass

            # 휩소 방지 장치 (Shakeout Protection Mode):
            # 진입 후 15분 미만이거나 장초반 15분 노이즈 구간인 경우
            # 미세한 트레일링 스톱 및 기술 지표 기반 탈출을 유예하여 '숨쉴 공간(Breathing Room)' 확보.
            is_shakeout_protection_active = (_hold_minutes < 15) or is_early_opening_noise

            if is_shakeout_protection_active:
                logger.debug("SHAKEOUT_PROTECTION_ACTIVE for {}: Hold minutes={:.1f}, Early opening={}. Trailing/Reversal exits suspended.",
                             symbol, _hold_minutes, is_early_opening_noise)

            # (1) ATR 기반 가변 손절 및 레짐 기반 손절 검사 (최우선 손절 라인)
            stop_sig = self._check_stop_loss(pos, price, atr_val, cfg)
            if stop_sig:
                logger.warning("🎯 HARD STOP / ATR STOP TRIGGERED: {} -> {}", symbol, stop_sig.reason)
                return stop_sig

            # (2) 익절 검사 (일반 익절 + 수익 3% 돌파 시 고점 대비 -1.5% 트레일링 락)
            tp_sig = self._check_take_profit(pos, price, pnl_pct, cfg)
            if tp_sig:
                logger.warning("🎯 TAKE PROFIT / TRAIL LOCK TRIGGERED: {} -> {}", symbol, tp_sig.reason)
                return tp_sig

            # 휩소 방지가 작동 중이지 않을 때만 민감한 트레일링 스톱 및 역추세 지표 감시
            if not is_shakeout_protection_active:
                # (3) 고성능 샹들리에 트레일링 스톱 검사 (수익 구간 비례 지수식 조임)
                trail_sig = self._check_trailing_stop(pos, price, atr_val, cfg)
                if trail_sig:
                    logger.warning("🎯 ADVANCED TRAILING STOP TRIGGERED: {} -> {}", symbol, trail_sig.reason)
                    return trail_sig

                # (4) 역추세 반전 지표 감시 (MACD 데드크로스, Bollinger/StochRSI 극단 과매수 청산)
                reversal_sig = self._check_reversal_signals(pos, indicators, price)
                if reversal_sig:
                    logger.warning("🎯 REVERSAL EXIT TRIGGERED: {} -> {}", symbol, reversal_sig.reason)
                    return reversal_sig

        except Exception as exit_e:
            logger.error("Advanced Adaptive Exit Engine error for {}: {}", symbol, exit_e)

        # 
        # [ ETF] ETF decay  5 (32.5h )  
        # 
        if symbol in getattr(config, 'INVERSE_ETFS', set()):
            if _hold_hours >= 32.5:
                return ExitSignal("SELL_ALL",
                    f"INVERSE_TIMEOUT: {_hold_hours/6.5:.1f} , decay  ",
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
        
        # ATR-based stop
        stop_mult = getattr(cfg, 'stop_loss_atr', 1.5)
        if pos.atr_at_entry > 0:
            stop_price = pos.entry_price - (pos.atr_at_entry * stop_mult)
        else:
            stop_price = pos.entry_price * 0.95
            
        # Regime-aware hard stop:
        # Bear market = tight 3% stop (was 5%  this was killing the R:R)
        # Bull/Neutral = 5% stop as before
        current_regime = getattr(self, '_last_regime', '')
        bear_regimes = {"BEAR_NORMAL", "BEAR_TRENDING", "BEAR_VOLATILE"}
        if current_regime in bear_regimes:
            hard_stop_pct = getattr(config, 'BEAR_HARD_STOP_PCT', 0.03)  # 3%
        else:
            hard_stop_pct = 0.05  # 5%
        
        hard_stop_price = pos.entry_price * (1 - hard_stop_pct)
        effective_stop = max(stop_price, hard_stop_price)
        
        if price <= effective_stop:
            reason = f"STOP: ${price:.2f} <= ${effective_stop:.2f} (ATR={pos.atr_at_entry:.2f})"
            if effective_stop == hard_stop_price:
                reason = f"HARD_STOP: P&L {pnl_pct:+.1%} <= -{hard_stop_pct:.0%}"
                
            return ExitSignal("SELL_ALL", reason, price, pnl_pct)
            
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
        
        # Absolute Hook: If we were 6% up, trailing stop CANNOT go below Entry + 1%.
        if breakeven_hook:
            trailing_stop = max(trailing_stop, pos.entry_price * 1.01)
        
        if price <= trailing_stop:
            pnl_pct = (price - pos.entry_price) / pos.entry_price
            return ExitSignal("SELL_ALL",
                            f"TRAIL(Lock): ${price:.2f} <= ${trailing_stop:.2f}",
                            price, pnl_pct)
        return None
    
    def _check_take_profit(self, pos: Position, price: float,
                          pnl_pct: float, cfg: PhaseConfig) -> Optional[ExitSignal]:
        """Take profit check with trailing profit lock"""
        # Standard TP
        if pnl_pct >= cfg.take_profit_pct and not pos.half_sold:
            return ExitSignal("SELL_ALL",
                            f"TP {pnl_pct:+.1%} >= {cfg.take_profit_pct:.0%}",
                            price, pnl_pct)
        
        # Trailing profit lock: Once up 3%, trail at -1.5% from peak (lock in gains)
        # This prevents +3% winners from turning into -5% losses
        if pos.high_since_entry > 0:
            peak_pnl = (pos.high_since_entry - pos.entry_price) / pos.entry_price
            if peak_pnl >= 0.03:
                trailing_lock = pos.high_since_entry * 0.985  # trail -1.5% from peak
                if price <= trailing_lock:
                    return ExitSignal("SELL_ALL",
                                    f"TRAIL_LOCK: peak +{peak_pnl:.1%}, locked at ${trailing_lock:.2f} (P&L {pnl_pct:+.1%})",
                                    price, pnl_pct)
        
        return None
    
    def _check_reversal_signals(self, pos: Position, ind: IndicatorSummary,
                               price: float) -> Optional[ExitSignal]:
        """Check for reversal indicators"""
        pnl_pct = (price - pos.entry_price) / pos.entry_price
        
        # MACD bearish cross
        if ind.macd.cross_down and pnl_pct > 0:
            return ExitSignal("SELL_ALL", "MACD bearish cross", price, pnl_pct)
        
        # Extreme overbought
        if ind.bollinger.percent_b > 1.05 and ind.rsi > 75:
            return ExitSignal("SELL_ALL", 
                            f"Overbought: BB%={ind.bollinger.percent_b:.2f}, RSI={ind.rsi:.0f}",
                            price, pnl_pct)
        
        # Stochastic RSI extreme + profit   
        if ind.stoch_rsi > 0.9 and pnl_pct > 0.02:
            return ExitSignal("SELL_ALL", f"StochRSI extreme: {ind.stoch_rsi:.2f}",
                            price, pnl_pct)
        
        return None
    
    # ==============================================
    # Position Management
    # ==============================================
    
    def add_position(self, symbol: str, entry_price: float, 
                    quantity: int, atr: float):
        """Add new position"""
        cfg = self.get_phase_config()
        #  ATR 0  5%   (DAWN    )
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
        except:
            pass
            
        for pos in api_positions:
            symbol = pos.symbol
            if symbol not in self._positions:
                # Retrieve true entry state if possible
                true_entry_time = datetime.now()
                true_high = max(pos.avg_price, pos.current_price)
                
                if db_mgr:
                    try:
                        # Find entry time from database
                        open_positions = db_mgr.get_open_positions()
                        matching = [p for p in open_positions if p['symbol'] == symbol]
                        if matching:
                            # entry_time in DB is a TIMESTAMP or iso-string
                            db_pos = matching[0]
                            db_entry_time = db_pos.get('entry_time')
                            if isinstance(db_entry_time, str):
                                try:
                                    db_entry_time = datetime.fromisoformat(db_entry_time)
                                except:
                                    pass
                            
                            if isinstance(db_entry_time, datetime):
                                true_entry_time = db_entry_time
                                logger.info("Recovered true entry time for {}: {}", symbol, true_entry_time)
                    except Exception as e:
                        logger.debug("Could not query true entry time for {}: {}", symbol, e)

                # ATR  
                df = self.fetch_data(symbol)
                atr = 0.0
                if df is not None and len(df) >= 14:
                    from indicators import calculate_atr
                    atr_series = calculate_atr(df)
                    atr = float(atr_series.iloc[-1]) if len(atr_series) > 0 else 0.0
                
                cfg = self.get_phase_config()
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
