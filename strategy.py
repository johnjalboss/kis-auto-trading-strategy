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

        _bear_regimes = {"BEAR_NORMAL", "BEAR_TRENDING", "BEAR_VOLATILE"}
        _choppy_regimes = {"CHOPPY", "TRANSITION", "CHOPPY_VOLATILE"}
        current_regime = getattr(self, '_last_regime', '')

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
            if ins_result.insider_sentiment == "SELLING" and (ins_result.insider_net_pct < -0.10 or ins_result.insider_net_value < -20_000_000):
                return EntrySignal("HOLD", 0, f"INSIDER_GUARD: Massive insider dumping detected ({ins_result.insider_net_pct:.3f}% of MC, Net: ${ins_result.insider_net_value/1e6:.1f}M)", 0)
        except Exception:
            pass

        # BREADTH_GUARD moved to the end of check_entry to support High-Score Bypass

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

        # Evaluate basic indicators filters (e.g. overbought check)
        cfg = self.get_phase_config()
        filter_res = self._check_entry_filters(indicators, cfg, symbol=symbol, price=current_price)
        
        # 10. DUAL-SETUP DECISION ENGINE
        # Setup A: Technical Chart Setup (52W High Breakout or Pullback in Uptrend)
        sma20 = df_daily['Close'].rolling(20).mean().iloc[-1]
        sma50 = df_daily['Close'].rolling(50).mean().iloc[-1]
        structural_uptrend = sma20 > sma50
        
        _52w_high = float(df_daily['High'].tail(252).max()) if len(df_daily) >= 252 else float(df_daily['High'].max())
        pct_from_high = (current_price - _52w_high) / _52w_high
        
        is_breakout = pct_from_high >= -0.025
        is_pullback = structural_uptrend and (38 <= indicators.rsi <= 65) and (current_price > sma50 * 0.985)
        
        # Setup B: Quant Liquidity Accumulation (Driven by heavy Dark Pool / CTA / Institutional Flows)
        # Allows entering a stock before technical breakout if flow conviction is extremely high.
        is_quant_accumulation = False
        if comp_signal and comp_signal.composite_score >= 70:
            # Requires heavy buying, positive OBV trend, and not overbought
            if indicators.obv_trend == "UP" and indicators.bollinger.percent_b < 0.75 and indicators.rsi < 68:
                is_quant_accumulation = True

        # Resolve setup type and baseline score addition
        setup_reason = ""
        if is_breakout:
            setup_reason = "SWING_BREAKOUT: 52W High Proximity"
        elif is_pullback:
            setup_reason = f"SWING_PULLBACK: RSI {indicators.rsi:.1f}, Trend UP"
        elif is_quant_accumulation:
            setup_reason = f"SWING_QUANT_ACCUMULATION: Score {comp_signal.composite_score:.0f} (Flow-driven)"
        else:
            return EntrySignal("HOLD", 0, "No Swing Setup (Not a Breakout, Pullback, or Quant Accumulation)", current_price)

        # 11. Dynamic score requirements based on Regime
        min_required = config.SCREENED_MIN_SCORE if is_screened else cfg.min_entry_score
        
        # Add buffer in choppy regimes to avoid whipsaws
        if current_regime in _choppy_regimes:
            min_required += 15
            setup_reason = f"[CHOPPY SELECTIVE] {setup_reason}"
            logger.info("CHOPPY SELECTIVE: Raised minimum score threshold for {} to {}", symbol, min_required)

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
        if current_regime in _bear_regimes:
            _allowed_in_bear = getattr(config, 'INVERSE_ETFS', set()) | getattr(config, 'DEFENSIVE_UNIVERSE_SET', set())
            if symbol not in _allowed_in_bear:
                if confidence < 80:
                    return EntrySignal("HOLD", confidence, f"BEAR_REGIME_BLOCK: {current_regime} (Score {confidence} < 80)", current_price)
                else:
                    setup_reason += f" | BEAR_BYPASS (Score {confidence} >= 80)"

        # 5. Market Breadth Guard with High-Score (>= 95) Bypass
        try:
            import kis_data as _kd
            _spy_df = _kd.get_daily_ohlcv("SPY", days=25)
            if _spy_df is not None and len(_spy_df) >= 22:
                _spy_close = _spy_df['Close']
                _spy_sma20 = float(_spy_close.rolling(20).mean().iloc[-1])
                _spy_current = float(_spy_close.iloc[-1])
                if _spy_current < _spy_sma20 * 0.995:
                    _allowed_in_downtrend = getattr(config, 'INVERSE_ETFS', set()) | getattr(config, 'DEFENSIVE_UNIVERSE_SET', set())
                    if symbol not in _allowed_in_downtrend:
                        if confidence < 95:
                            return EntrySignal("HOLD", confidence, f"BREADTH_GUARD: SPY (${_spy_current:.1f}) below SMA20 (${_spy_sma20:.1f}) (Score {confidence} < 95)", current_price)
                        else:
                            setup_reason += f" | BREADTH_BYPASS (Score {confidence} >= 95)"
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

            # timezone 
            if _entry_raw.tzinfo is not None and _now_raw.tzinfo is None:
                _entry_raw = _entry_raw.replace(tzinfo=None)
            elif _entry_raw.tzinfo is None and _now_raw.tzinfo is not None:
                _now_raw = _now_raw.replace(tzinfo=None)

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
        
        # Dynamic HMM Regime Scaling for ATR stop multiplier
        current_regime = getattr(self, '_last_regime', '')
        bear_regimes = {"BEAR_NORMAL", "BEAR_TRENDING", "BEAR_VOLATILE"}
        choppy_regimes = {"CHOPPY", "TRANSITION", "CHOPPY_VOLATILE"}
        
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
        # Bear market = tight 3% stop (was 5%  this was killing the R:R)
        # Bull/Neutral = 5% stop as before
        if current_regime in bear_regimes:
            hard_stop_pct = getattr(config, 'BEAR_HARD_STOP_PCT', 0.03)  # 3%
        else:
            hard_stop_pct = 0.05  # 5%
        
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
        """Take profit check with Scale-Out (1.5R half-sell, 3.0R final sell) and regime scaling"""
        current_regime = getattr(self, '_last_regime', '')
        bear_regimes = {"BEAR_NORMAL", "BEAR_TRENDING", "BEAR_VOLATILE"}
        choppy_regimes = {"CHOPPY", "TRANSITION", "CHOPPY_VOLATILE"}
        
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
            
        # Scale-Out TP Exits
        if not pos.half_sold:
            if price >= target_15r:
                return ExitSignal("SELL_HALF",
                                f"SCALE_OUT_1.5R: {pnl_pct:+.1%} >= 1.5R target (${target_15r:.2f})",
                                price, pnl_pct)
        else:
            if price >= target_30r:
                return ExitSignal("SELL_ALL",
                                f"FINAL_TP_3.0R: {pnl_pct:+.1%} >= 3.0R target (${target_30r:.2f})",
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
        if ind.macd.cross_down and pnl_pct > 0:
            return ExitSignal("SELL_ALL", "MACD bearish cross", price, pnl_pct)
        
        # Extreme overbought — only exit if we actually have profit to protect
        # [v1.1.8] Added pnl_pct > 0.01: previously selling at BB%=1.05 even at breakeven (avg +0.02%)
        if ind.bollinger.percent_b > 1.05 and ind.rsi > 75 and pnl_pct > 0.01:
            return ExitSignal("SELL_ALL", 
                            f"Overbought: BB%={ind.bollinger.percent_b:.2f}, RSI={ind.rsi:.0f}",
                            price, pnl_pct)
        
        # Stochastic RSI extreme + profit
        # [v1.1.8] Raised from 2% -> 4%: data showed StochRSI exits avg +2.58% but cutting too early
        if ind.stoch_rsi > 0.9 and pnl_pct > 0.04:
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
