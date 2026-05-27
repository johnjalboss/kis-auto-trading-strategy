"""
Market Regime Detector
========================
Detect current market regime using multiple signals.

Regimes:
1. BULL_TRENDING - Strong uptrend, low volatility
2. BULL_VOLATILE - Uptrend with high volatility
3. BEAR_TRENDING - Strong downtrend
4. BEAR_VOLATILE - Downtrend with capitulation
5. RANGE_BOUND - Sideways consolidation
6. TRANSITION - Regime change in progress
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


class MarketRegime(Enum):
    BULL_TRENDING = "BULL_TRENDING"
    BULL_VOLATILE = "BULL_VOLATILE"
    BEAR_TRENDING = "BEAR_TRENDING"
    BEAR_VOLATILE = "BEAR_VOLATILE"
    RANGE_BOUND = "RANGE_BOUND"
    TRANSITION = "TRANSITION"


@dataclass
class RegimeSignal:
    """Market regime analysis"""
    current_regime: MarketRegime
    regime_confidence: int  # 0-100
    regime_duration_days: int
    
    # Trend metrics
    trend_direction: str  # "UP", "DOWN", "FLAT"
    trend_strength: float  # 0-100 (ADX-based)
    price_vs_200ma: float  # % above/below
    
    # Volatility metrics
    current_volatility: float
    volatility_regime: str  # "LOW", "NORMAL", "HIGH", "EXTREME"
    vix_level: float
    vix_percentile: float  # vs 1-year
    
    # Breadth metrics
    pct_above_50ma: float
    advance_decline: float
    
    # Recommended strategy
    strategy: str
    position_size_mult: float  # 0.0-1.5
    
    regime_score: int  # -100 to +100
    details: List[str]


class RegimeDetector:
    """
    Advanced Market Regime Detection
    
    Uses multiple inputs:
    1. Trend: Price vs MAs, ADX
    2. Volatility: VIX level and percentile
    3. Breadth: % stocks above 50MA
    4. Momentum: Rate of change
    
    Regime Strategies:
    - BULL_TRENDING: Aggressive long, buy dips
    - BULL_VOLATILE: Reduce size, quick profits
    - BEAR_TRENDING: Short or cash, no longs
    - BEAR_VOLATILE: Cash is king, wait
    - RANGE_BOUND: Mean reversion plays
    - TRANSITION: Reduce exposure
    """
    
    def __init__(self):
        self._cache: Dict[str, pd.DataFrame] = {}
    
    def analyze(self) -> RegimeSignal:
        """Detect current market regime"""
        details = []
        
        # Fetch SPY data
        spy = self._fetch_data("SPY")
        vix = self._fetch_data("^VIX")
        
        if spy is None or len(spy) < 50:
            return self._unknown_result()
        
        close = spy['Close']
        current = close.iloc[-1]
        
        # 1. Trend Analysis
        sma50 = close.rolling(50).mean().iloc[-1]
        sma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else close.mean()
        
        price_vs_200ma = (current / sma200 - 1) * 100
        price_vs_50ma = (current / sma50 - 1) * 100
        
        # ADX for trend strength
        adx = self._calculate_adx(spy)
        
        if price_vs_200ma > 5 and price_vs_50ma > 0:
            trend_dir = "UP"
        elif price_vs_200ma < -5 and price_vs_50ma < 0:
            trend_dir = "DOWN"
        else:
            trend_dir = "FLAT"
        
        # 2. Volatility Analysis
        returns = close.pct_change().dropna()
        current_vol = returns.tail(20).std() * np.sqrt(252) * 100
        hist_vol = returns.std() * np.sqrt(252) * 100
        
        vix_level = float(vix['Close'].iloc[-1]) if vix is not None and not vix.empty else 20
        vix_1y = vix['Close'].tail(252) if vix is not None and len(vix) >= 252 else pd.Series([20])
        vix_percentile = (vix_level - vix_1y.min()) / (vix_1y.max() - vix_1y.min()) * 100 if vix_1y.max() != vix_1y.min() else 50
        
        if vix_level > 35:
            vol_regime = "EXTREME"
        elif vix_level > 25:
            vol_regime = "HIGH"
        elif vix_level > 15:
            vol_regime = "NORMAL"
        else:
            vol_regime = "LOW"
        
        # 3. Breadth (simplified)
        pct_above_50ma = 0.6  # Would calculate from universe
        ad_ratio = 1.2  # Would calculate
        
        # 4. Determine Regime
        if trend_dir == "UP":
            if vol_regime in ["LOW", "NORMAL"] and adx > 25:
                regime = MarketRegime.BULL_TRENDING
                confidence = 85
                strategy = "AGGRESSIVE_LONG"
                size_mult = 1.2
                details.append("STRONG_UPTREND")
            else:
                regime = MarketRegime.BULL_VOLATILE
                confidence = 70
                strategy = "CAUTIOUS_LONG"
                size_mult = 0.8
                details.append("VOLATILE_UPTREND")
        
        elif trend_dir == "DOWN":
            if vol_regime in ["HIGH", "EXTREME"]:
                regime = MarketRegime.BEAR_VOLATILE
                confidence = 80
                strategy = "CASH_OR_HEDGE"
                size_mult = 0.3
                details.append("CAPITULATION_RISK")
            else:
                regime = MarketRegime.BEAR_TRENDING
                confidence = 75
                strategy = "DEFENSIVE"
                size_mult = 0.5
                details.append("DOWNTREND")
        
        else:  # FLAT
            if adx < 20:
                regime = MarketRegime.RANGE_BOUND
                confidence = 70
                strategy = "MEAN_REVERSION"
                size_mult = 0.7
                details.append("RANGE_TRADING")
            else:
                regime = MarketRegime.TRANSITION
                confidence = 50
                strategy = "WAIT_AND_SEE"
                size_mult = 0.5
                details.append("REGIME_CHANGE")
        
        # Calculate score
        score = 0
        if regime in [MarketRegime.BULL_TRENDING]:
            score = 60
        elif regime in [MarketRegime.BULL_VOLATILE]:
            score = 30
        elif regime == MarketRegime.RANGE_BOUND:
            score = 0
        elif regime == MarketRegime.BEAR_TRENDING:
            score = -40
        elif regime == MarketRegime.BEAR_VOLATILE:
            score = -70
        else:
            score = -20

        # ============================================================
        # 📊 CTA Trend-Following Systematic Flow Model
        # ============================================================
        cta_signal = "NEUTRAL"
        cta_score = 0
        try:
            # Check 200-day and 50-day SMA crossovers over the last 5 days
            spy_close_5d = close.tail(5)
            sma200_5d = close.rolling(200).mean().tail(5) if len(close) >= 200 else pd.Series([sma200]*5, index=spy_close_5d.index)
            sma50_5d = close.rolling(50).mean().tail(5)
            
            # Did we cross above 200-day SMA? (Bullish CTA Buy Cascade)
            crossed_above_200 = (spy_close_5d.iloc[-5] < sma200_5d.iloc[-5]) and (spy_close_5d.iloc[-1] > sma200_5d.iloc[-1])
            # Did we cross below 200-day SMA? (Bearish CTA Liquidation)
            crossed_below_200 = (spy_close_5d.iloc[-5] > sma200_5d.iloc[-5]) and (spy_close_5d.iloc[-1] < sma200_5d.iloc[-1])
            
            # Did we cross above 50-day SMA?
            crossed_above_50 = (spy_close_5d.iloc[-5] < sma50_5d.iloc[-5]) and (spy_close_5d.iloc[-1] > sma50_5d.iloc[-1])
            # Did we cross below 50-day SMA?
            crossed_below_50 = (spy_close_5d.iloc[-5] > sma50_5d.iloc[-5]) and (spy_close_5d.iloc[-1] < sma50_5d.iloc[-1])
            
            if crossed_above_200:
                cta_signal = "BULLISH_BUY_CASCADE"
                cta_score = 30
                details.append("CTA_FLOW: Crossed ABOVE 200MA (Bullish Buy Cascade)")
            elif crossed_above_50:
                cta_signal = "BULLISH_MOMENTUM_FLOW"
                cta_score = 15
                details.append("CTA_FLOW: Crossed ABOVE 50MA (Bullish Momentum Flow)")
            elif crossed_below_200:
                cta_signal = "BEARISH_LIQUIDATION_CASCADE"
                cta_score = -35
                details.append("CTA_FLOW: Crossed BELOW 200MA (Bearish Liquidation Cascade)")
            elif crossed_below_50:
                cta_signal = "BEARISH_MOMENTUM_EXIT"
                cta_score = -20
                details.append("CTA_FLOW: Crossed BELOW 50MA (Bearish Momentum Exit)")
            else:
                # If price is stably above 200MA and 50MA, CTA trend is already fully long
                if current > sma200 and current > sma50:
                    cta_signal = "STABLE_LONG_ALLOCATION"
                    cta_score = 10
                elif current < sma200 and current < sma50:
                    cta_signal = "STABLE_SHORT_ALLOCATION"
                    cta_score = -10
        except Exception as e:
            logger.debug("CTA Flow modeling calculation failed: {}", e)
            
        score += cta_score
        # ============================================================
        
        # VIX impact
        if vix_level > 30:
            score -= 20
            details.append(f"VIX_HIGH:{vix_level:.0f}")
        elif vix_level < 15:
            score += 10
            details.append(f"VIX_LOW:{vix_level:.0f}")
        
        # Estimate regime duration
        duration = self._estimate_regime_duration(spy, regime)
        
        return RegimeSignal(
            current_regime=regime,
            regime_confidence=confidence,
            regime_duration_days=duration,
            trend_direction=trend_dir,
            trend_strength=adx,
            price_vs_200ma=price_vs_200ma,
            current_volatility=current_vol,
            volatility_regime=vol_regime,
            vix_level=vix_level,
            vix_percentile=vix_percentile,
            pct_above_50ma=pct_above_50ma,
            advance_decline=ad_ratio,
            strategy=strategy,
            position_size_mult=size_mult,
            regime_score=max(-100, min(100, score)),
            details=details
        )
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate ADX"""
        high = df['High']
        low = df['Low']
        close = df['Close']
        
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
        
        tr = pd.DataFrame({
            'hl': high - low,
            'hc': abs(high - close.shift()),
            'lc': abs(low - close.shift())
        }).max(axis=1)
        
        atr = tr.rolling(period).mean()
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, 1)
        adx = dx.rolling(period).mean()
        
        return float(adx.iloc[-1]) if not pd.isna(adx.iloc[-1]) else 25
    
    def _estimate_regime_duration(self, df: pd.DataFrame, regime: MarketRegime) -> int:
        """Estimate how long current regime has been active"""
        close = df['Close']
        sma50 = close.rolling(50).mean()
        
        # Count days in current trend
        if regime in [MarketRegime.BULL_TRENDING, MarketRegime.BULL_VOLATILE]:
            above_50 = close > sma50
            duration = 0
            for i in range(len(above_50) - 1, -1, -1):
                if above_50.iloc[i]:
                    duration += 1
                else:
                    break
        else:
            below_50 = close < sma50
            duration = 0
            for i in range(len(below_50) - 1, -1, -1):
                if below_50.iloc[i]:
                    duration += 1
                else:
                    break
        
        return duration
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch data"""
        try:
            df = yf.download(symbol, period='1y', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return None
    
    def _unknown_result(self) -> RegimeSignal:
        """Unknown result"""
        return RegimeSignal(
            current_regime=MarketRegime.TRANSITION,
            regime_confidence=0, regime_duration_days=0,
            trend_direction="UNKNOWN", trend_strength=0, price_vs_200ma=0,
            current_volatility=0, volatility_regime="UNKNOWN",
            vix_level=20, vix_percentile=50,
            pct_above_50ma=0.5, advance_decline=1.0,
            strategy="WAIT", position_size_mult=0.5,
            regime_score=0, details=[]
        )


# Global
_detector = None

def get_regime_detector() -> RegimeDetector:
    global _detector
    if _detector is None:
        _detector = RegimeDetector()
    return _detector


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing RegimeDetector...")
    
    detector = RegimeDetector()
    result = detector.analyze()
    
    print(f"\n{'='*60}")
    print("MARKET REGIME ANALYSIS")
    print('='*60)
    print(f"🎯 Regime: {result.current_regime.value}")
    print(f"📊 Confidence: {result.regime_confidence}%")
    print(f"📅 Duration: {result.regime_duration_days} days")
    print()
    print(f"Trend: {result.trend_direction} (ADX: {result.trend_strength:.0f})")
    print(f"Price vs 200MA: {result.price_vs_200ma:+.1f}%")
    print()
    print(f"VIX: {result.vix_level:.1f} ({result.vix_percentile:.0f}th percentile)")
    print(f"Volatility Regime: {result.volatility_regime}")
    print()
    print(f"💡 Strategy: {result.strategy}")
    print(f"📐 Position Size: {result.position_size_mult:.1f}x")
    print(f"Score: {result.regime_score:+d}")
    print(f"Details: {result.details}")
