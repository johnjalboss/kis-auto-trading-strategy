"""
Market Internals Analyzer
===========================
Analyze market-wide breadth and internals.

Metrics:
1. NYSE TICK - Upticks vs Downticks
2. TRIN (Arms Index) - Volume flow
3. Advance/Decline - Market breadth
4. Put/Call Ratio - Options sentiment
5. New Highs/Lows
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class InternalsSignal:
    """Market internals analysis"""
    # Breadth
    advance_decline_ratio: float
    advance_decline_5d: float
    mcclellan_oscillator: float
    
    # Volume internals
    up_volume_ratio: float
    trin: float  # Arms Index
    trin_signal: str  # "BULLISH", "BEARISH", "NEUTRAL"
    
    # Sentiment
    put_call_ratio: float
    put_call_signal: str
    vix_term_structure: str
    
    # New Highs/Lows
    new_highs: int
    new_lows: int
    hi_lo_ratio: float
    
    # Overall
    internals_regime: str  # "STRONG_BULL", "BULL", "NEUTRAL", "BEAR", "STRONG_BEAR"
    confirmation: bool  # Does internals confirm price trend?
    
    internals_score: int  # -100 to +100
    details: List[str]


class MarketInternalsAnalyzer:
    """
    Market Internals & Breadth Analysis
    
    Key Indicators:
    
    1. TRIN (Arms Index)
       - < 0.8 = Very Bullish
       - 0.8-1.0 = Bullish
       - 1.0-1.2 = Bearish
       - > 1.2 = Very Bearish
    
    2. Put/Call Ratio
       - < 0.7 = Complacency (bearish)
       - 0.7-1.0 = Neutral
       - > 1.0 = Fear (contrarian bullish)
    
    3. New Highs/Lows
       - Expansion in new highs = bullish
       - Expansion in new lows = bearish
    
    Scoring:
    - Strong breadth: +30
    - TRIN bullish: +20
    - Put/Call fear: +25
    - Weak breadth: -30
    """
    
    def __init__(self):
        pass
    
    def analyze(self) -> InternalsSignal:
        """Analyze market internals"""
        details = []
        score = 0
        
        # Fetch market data for breadth proxy
        spy = self._fetch_data("SPY")
        vix = self._fetch_data("^VIX")
        
        if spy is None or len(spy) < 20:
            return self._default_result()
        
        close = spy['Close']
        volume = spy['Volume']
        
        # 1. Advance/Decline proxy (from price action)
        returns = close.diff()
        advances = (returns > 0).rolling(5).sum().iloc[-1]
        declines = (returns < 0).rolling(5).sum().iloc[-1]
        
        ad_ratio = advances / max(declines, 0.1)
        ad_5d = advances - declines
        
        # McClellan oscillator proxy
        mcclellan = (returns.tail(19).mean() - returns.tail(39).mean()) / close.iloc[-1] * 1000
        
        if ad_ratio > 1.5:
            score += 25
            details.append("STRONG_BREADTH")
        elif ad_ratio > 1:
            score += 10
        elif ad_ratio < 0.67:
            score -= 25
            details.append("WEAK_BREADTH")
        elif ad_ratio < 1:
            score -= 10
        
        # 2. Volume internals (TRIN proxy)
        up_days = returns > 0
        down_days = returns < 0
        
        # Align indices for volume masking
        recent_up = up_days.tail(5)
        recent_down = down_days.tail(5)
        recent_vol = volume.tail(5)
        
        up_vol = float(recent_vol[recent_up].mean()) if recent_up.any() else 0
        down_vol = float(recent_vol[recent_down].mean()) if recent_down.any() else 1
        
        up_vol_ratio = up_vol / (up_vol + down_vol) if (up_vol + down_vol) > 0 else 0.5
        
        # TRIN calculation (simplified)
        trin = (declines / max(advances, 0.1)) / (down_vol / max(up_vol, 1))
        trin = max(0.5, min(2.0, trin))
        
        if trin < 0.8:
            trin_signal = "VERY_BULLISH"
            score += 25
            details.append("TRIN_BULLISH")
        elif trin < 1.0:
            trin_signal = "BULLISH"
            score += 10
        elif trin > 1.2:
            trin_signal = "VERY_BEARISH"
            score -= 25
            details.append("TRIN_BEARISH")
        elif trin > 1.0:
            trin_signal = "BEARISH"
            score -= 10
        else:
            trin_signal = "NEUTRAL"
        
        # 3. Put/Call ratio proxy (from VIX)
        vix_level = float(vix['Close'].iloc[-1]) if vix is not None and not vix.empty else 20
        
        # Estimate put/call from VIX
        if vix_level > 25:
            put_call = 1.2
            put_call_signal = "FEAR"
            score += 20  # Contrarian bullish
            details.append("HIGH_FEAR:Contrarian")
        elif vix_level > 20:
            put_call = 0.9
            put_call_signal = "NEUTRAL"
        elif vix_level < 15:
            put_call = 0.6
            put_call_signal = "COMPLACENCY"
            score -= 15
            details.append("COMPLACENCY")
        else:
            put_call = 0.8
            put_call_signal = "NEUTRAL"
        
        # VIX term structure (proxy)
        vix_5d_ago = float(vix['Close'].iloc[-5]) if vix is not None and len(vix) >= 5 else vix_level
        if vix_level > vix_5d_ago * 1.1:
            vix_term = "BACKWARDATION"
        elif vix_level < vix_5d_ago * 0.9:
            vix_term = "CONTANGO"
        else:
            vix_term = "FLAT"
        
        # 4. New Highs/Lows (simulated)
        rolling_high = close.rolling(52).max()
        rolling_low = close.rolling(52).min()
        
        new_highs = 1 if close.iloc[-1] >= rolling_high.iloc[-1] * 0.98 else 0
        new_lows = 1 if close.iloc[-1] <= rolling_low.iloc[-1] * 1.02 else 0
        hi_lo_ratio = 2 if new_highs else (0.5 if new_lows else 1)
        
        # 5. Overall regime
        if score >= 40:
            regime = "STRONG_BULL"
        elif score >= 15:
            regime = "BULL"
        elif score <= -40:
            regime = "STRONG_BEAR"
        elif score <= -15:
            regime = "BEAR"
        else:
            regime = "NEUTRAL"
        
        # 6. Confirmation check
        price_trend_up = close.iloc[-1] > close.iloc[-5]
        confirmation = (price_trend_up and score > 0) or (not price_trend_up and score < 0)
        
        if not confirmation and abs(score) > 20:
            details.append("⚠️ DIVERGENCE")
        
        return InternalsSignal(
            advance_decline_ratio=ad_ratio,
            advance_decline_5d=ad_5d,
            mcclellan_oscillator=mcclellan,
            up_volume_ratio=up_vol_ratio,
            trin=trin,
            trin_signal=trin_signal,
            put_call_ratio=put_call,
            put_call_signal=put_call_signal,
            vix_term_structure=vix_term,
            new_highs=new_highs,
            new_lows=new_lows,
            hi_lo_ratio=hi_lo_ratio,
            internals_regime=regime,
            confirmation=confirmation,
            internals_score=max(-100, min(100, score)),
            details=details
        )
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch data"""
        try:
            df = yf.download(symbol, period='60d', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return None
    
    def _default_result(self) -> InternalsSignal:
        """Default result"""
        return InternalsSignal(
            advance_decline_ratio=1, advance_decline_5d=0, mcclellan_oscillator=0,
            up_volume_ratio=0.5, trin=1.0, trin_signal="NEUTRAL",
            put_call_ratio=0.9, put_call_signal="NEUTRAL", vix_term_structure="FLAT",
            new_highs=0, new_lows=0, hi_lo_ratio=1,
            internals_regime="NEUTRAL", confirmation=True,
            internals_score=0, details=[]
        )


# Global
_analyzer = None

def get_internals_analyzer() -> MarketInternalsAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = MarketInternalsAnalyzer()
    return _analyzer


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing MarketInternalsAnalyzer...")
    
    analyzer = MarketInternalsAnalyzer()
    result = analyzer.analyze()
    
    print(f"\n{'='*60}")
    print("MARKET INTERNALS")
    print('='*60)
    print(f"Regime: {result.internals_regime}")
    print(f"Score: {result.internals_score:+d}")
    print(f"Confirmation: {result.confirmation}")
    print()
    print(f"A/D Ratio: {result.advance_decline_ratio:.2f}")
    print(f"McClellan: {result.mcclellan_oscillator:.2f}")
    print(f"Up Volume %: {result.up_volume_ratio:.1%}")
    print()
    print(f"TRIN: {result.trin:.2f} ({result.trin_signal})")
    print(f"Put/Call: {result.put_call_ratio:.2f} ({result.put_call_signal})")
    print(f"VIX Structure: {result.vix_term_structure}")
    print()
    print(f"Hi/Lo Ratio: {result.hi_lo_ratio:.2f}")
    print(f"Details: {result.details}")
