"""
Accumulation/Distribution Pattern Detector
============================================
Detect Wyckoff accumulation/distribution patterns.

Phases:
1. Accumulation: Smart money buying before markup
2. Distribution: Smart money selling before markdown
3. Markup/Markdown: Trend phases
"""

from dataclasses import dataclass
from typing import Optional, List, Dict
from enum import Enum
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


class WyckoffPhase(Enum):
    ACCUMULATION = "ACCUMULATION"   # Bottom, smart money buying
    MARKUP = "MARKUP"               # Uptrend
    DISTRIBUTION = "DISTRIBUTION"   # Top, smart money selling
    MARKDOWN = "MARKDOWN"           # Downtrend
    UNKNOWN = "UNKNOWN"


@dataclass
class AccumulationSignal:
    """Accumulation/Distribution analysis"""
    symbol: str
    
    phase: WyckoffPhase
    phase_confidence: int  # 0-100
    
    # Pattern detection
    has_spring: bool       # Test of support with reversal
    has_upthrust: bool     # Test of resistance with reversal
    sos_detected: bool     # Sign of Strength
    sow_detected: bool     # Sign of Weakness
    
    # Volume patterns
    volume_declining_in_range: bool
    volume_expansion_on_breakout: bool
    
    # Price patterns
    higher_lows: bool
    lower_highs: bool
    
    score: int  # -100 to +100
    signal: str
    details: List[str]


class AccumulationDetector:
    """
    Wyckoff Accumulation/Distribution Detector
    
    Accumulation Signs (Bullish):
    1. Price in trading range after downtrend
    2. Volume declining in range
    3. Spring (false breakdown with reversal)
    4. Higher lows forming
    5. SOS (Sign of Strength) - high volume rally
    
    Distribution Signs (Bearish):
    1. Price in trading range after uptrend
    2. Volume declining in range
    3. Upthrust (false breakout with reversal)
    4. Lower highs forming
    5. SOW (Sign of Weakness) - high volume decline
    """
    
    def __init__(self, lookback: int = 60):
        self.lookback = lookback
    
    def analyze(self, symbol: str) -> AccumulationSignal:
        """Analyze for accumulation/distribution"""
        df = self._fetch_data(symbol)
        
        if df is None or len(df) < 40:
            return self._unknown_result(symbol)
        
        details = []
        score = 0
        
        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume']
        
        # 1. Determine if in trading range
        in_range, range_high, range_low = self._detect_trading_range(df)
        
        if not in_range:
            # Check for trending
            if close.iloc[-1] > close.iloc[-20]:
                phase = WyckoffPhase.MARKUP
                score += 20
            else:
                phase = WyckoffPhase.MARKDOWN
                score -= 20
            details.append(f"TRENDING:{phase.value}")
        else:
            # In range - check for accumulation or distribution
            prior_trend = self._get_prior_trend(df)
            
            if prior_trend == "DOWN":
                phase = WyckoffPhase.ACCUMULATION
                score += 30
                details.append("RANGE_AFTER_DOWNTREND")
            else:
                phase = WyckoffPhase.DISTRIBUTION
                score -= 30
                details.append("RANGE_AFTER_UPTREND")
        
        # 2. Volume analysis in range
        vol_declining = self._volume_declining_in_range(df)
        if vol_declining and in_range:
            score += 10
            details.append("VOLUME_DECLINING")
        
        # 3. Spring detection (bullish)
        has_spring = self._detect_spring(df)
        if has_spring:
            score += 30
            details.append("SPRING_DETECTED")
        
        # 4. Upthrust detection (bearish)
        has_upthrust = self._detect_upthrust(df)
        if has_upthrust:
            score -= 30
            details.append("UPTHRUST_DETECTED")
        
        # 5. Higher lows / Lower highs
        higher_lows = self._detect_higher_lows(df)
        lower_highs = self._detect_lower_highs(df)
        
        if higher_lows:
            score += 20
            details.append("HIGHER_LOWS")
        if lower_highs:
            score -= 20
            details.append("LOWER_HIGHS")
        
        # 6. SOS/SOW detection
        sos = self._detect_sos(df)
        sow = self._detect_sow(df)
        
        if sos:
            score += 25
            details.append("SIGN_OF_STRENGTH")
        if sow:
            score -= 25
            details.append("SIGN_OF_WEAKNESS")
        
        # 7. Breakout volume
        vol_expansion = self._volume_expansion_on_breakout(df)
        
        # Determine signal
        if score >= 50:
            signal = "STRONG_ACCUMULATION"
        elif score >= 20:
            signal = "ACCUMULATION"
        elif score <= -50:
            signal = "STRONG_DISTRIBUTION"
        elif score <= -20:
            signal = "DISTRIBUTION"
        else:
            signal = "NEUTRAL"
        
        # Phase confidence
        confidence = min(100, abs(score))
        
        return AccumulationSignal(
            symbol=symbol,
            phase=phase,
            phase_confidence=confidence,
            has_spring=has_spring,
            has_upthrust=has_upthrust,
            sos_detected=sos,
            sow_detected=sow,
            volume_declining_in_range=vol_declining,
            volume_expansion_on_breakout=vol_expansion,
            higher_lows=higher_lows,
            lower_highs=lower_highs,
            score=max(-100, min(100, score)),
            signal=signal,
            details=details
        )
    
    def _detect_trading_range(self, df: pd.DataFrame, window: int = 20) -> tuple:
        """Detect if price is in trading range"""
        high = df['High'].tail(window)
        low = df['Low'].tail(window)
        close = df['Close'].tail(window)
        
        range_high = high.max()
        range_low = low.min()
        range_size = (range_high - range_low) / range_low
        
        # Trading range = price movement < 15% in window
        in_range = range_size < 0.15
        
        return in_range, range_high, range_low
    
    def _get_prior_trend(self, df: pd.DataFrame) -> str:
        """Get trend prior to current range"""
        # Look at bars 20-40 back
        close = df['Close'].iloc[-40:-20]
        
        if close.iloc[-1] < close.iloc[0]:
            return "DOWN"
        return "UP"
    
    def _volume_declining_in_range(self, df: pd.DataFrame) -> bool:
        """Check if volume is declining in current range"""
        volume = df['Volume'].tail(20)
        
        first_half_avg = volume.iloc[:10].mean()
        second_half_avg = volume.iloc[10:].mean()
        
        return second_half_avg < first_half_avg * 0.8
    
    def _detect_spring(self, df: pd.DataFrame) -> bool:
        """Detect spring (false breakdown with reversal)"""
        # Look for: Price breaks below support, then closes back above
        low = df['Low'].tail(20)
        close = df['Close'].tail(20)
        
        support = low.iloc[:15].min()
        
        # Recent bar went below support but closed above
        for i in range(-5, 0):
            if low.iloc[i] < support and close.iloc[i] > support:
                return True
        
        return False
    
    def _detect_upthrust(self, df: pd.DataFrame) -> bool:
        """Detect upthrust (false breakout with reversal)"""
        high = df['High'].tail(20)
        close = df['Close'].tail(20)
        
        resistance = high.iloc[:15].max()
        
        # Recent bar went above resistance but closed below
        for i in range(-5, 0):
            if high.iloc[i] > resistance and close.iloc[i] < resistance:
                return True
        
        return False
    
    def _detect_higher_lows(self, df: pd.DataFrame) -> bool:
        """Detect higher lows pattern"""
        low = df['Low'].tail(15)
        
        # Find swing lows
        swing_lows = []
        for i in range(2, len(low) - 2):
            if low.iloc[i] < low.iloc[i-1] and low.iloc[i] < low.iloc[i-2]:
                if low.iloc[i] < low.iloc[i+1] and low.iloc[i] < low.iloc[i+2]:
                    swing_lows.append(low.iloc[i])
        
        if len(swing_lows) >= 2:
            return swing_lows[-1] > swing_lows[0]
        
        return False
    
    def _detect_lower_highs(self, df: pd.DataFrame) -> bool:
        """Detect lower highs pattern"""
        high = df['High'].tail(15)
        
        # Find swing highs
        swing_highs = []
        for i in range(2, len(high) - 2):
            if high.iloc[i] > high.iloc[i-1] and high.iloc[i] > high.iloc[i-2]:
                if high.iloc[i] > high.iloc[i+1] and high.iloc[i] > high.iloc[i+2]:
                    swing_highs.append(high.iloc[i])
        
        if len(swing_highs) >= 2:
            return swing_highs[-1] < swing_highs[0]
        
        return False
    
    def _detect_sos(self, df: pd.DataFrame) -> bool:
        """Detect Sign of Strength (high volume rally)"""
        close = df['Close'].tail(10)
        volume = df['Volume'].tail(10)
        
        vol_avg = df['Volume'].tail(20).mean()
        
        # Strong rally on high volume
        price_change = close.iloc[-1] / close.iloc[0] - 1
        recent_vol = volume.iloc[-3:].mean()
        
        return price_change > 0.03 and recent_vol > vol_avg * 1.5
    
    def _detect_sow(self, df: pd.DataFrame) -> bool:
        """Detect Sign of Weakness (high volume decline)"""
        close = df['Close'].tail(10)
        volume = df['Volume'].tail(10)
        
        vol_avg = df['Volume'].tail(20).mean()
        
        # Strong decline on high volume
        price_change = close.iloc[-1] / close.iloc[0] - 1
        recent_vol = volume.iloc[-3:].mean()
        
        return price_change < -0.03 and recent_vol > vol_avg * 1.5
    
    def _volume_expansion_on_breakout(self, df: pd.DataFrame) -> bool:
        """Check for volume expansion on breakout"""
        close = df['Close']
        volume = df['Volume']
        
        vol_avg = volume.tail(20).mean()
        recent_vol = volume.iloc[-1]
        
        # Price at new high with high volume
        high_20 = close.tail(20).max()
        
        return close.iloc[-1] >= high_20 * 0.99 and recent_vol > vol_avg * 1.5
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch data"""
        try:
            df = yf.download(symbol, period=f'{self.lookback}d', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return None
    
    def _unknown_result(self, symbol: str) -> AccumulationSignal:
        """Return unknown result"""
        return AccumulationSignal(
            symbol=symbol, phase=WyckoffPhase.UNKNOWN, phase_confidence=0,
            has_spring=False, has_upthrust=False, sos_detected=False, sow_detected=False,
            volume_declining_in_range=False, volume_expansion_on_breakout=False,
            higher_lows=False, lower_highs=False, score=0, signal="UNKNOWN", details=[]
        )


# Global instance
_detector = None

def get_accumulation_detector() -> AccumulationDetector:
    global _detector
    if _detector is None:
        _detector = AccumulationDetector()
    return _detector


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing AccumulationDetector...")
    
    detector = AccumulationDetector()
    
    for symbol in ["AAPL", "TSLA", "NVDA"]:
        print(f"\n{'='*50}")
        print(f"{symbol}")
        print('='*50)
        
        result = detector.analyze(symbol)
        
        print(f"Phase: {result.phase.value} ({result.phase_confidence}%)")
        print(f"Signal: {result.signal} ({result.score:+d})")
        print(f"Spring: {result.has_spring} | Upthrust: {result.has_upthrust}")
        print(f"SOS: {result.sos_detected} | SOW: {result.sow_detected}")
        print(f"Higher Lows: {result.higher_lows} | Lower Highs: {result.lower_highs}")
        print(f"Details: {result.details}")
