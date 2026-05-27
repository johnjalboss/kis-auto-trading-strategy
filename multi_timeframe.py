"""
Multi-Timeframe Confluence
============================
Confirm signals across multiple timeframes.
"""

from dataclasses import dataclass
from typing import List, Optional
import pandas as pd
import numpy as np
import kis_data as yf
from loguru import logger


@dataclass
class TimeframeSignal:
    timeframe: str
    trend: str  # "BULLISH", "BEARISH", "NEUTRAL"
    strength: int  # 0-100
    key_level: float
    details: List[str]


@dataclass
class ConfluenceResult:
    symbol: str
    signals: List[TimeframeSignal]
    
    confluence_score: int  # 0-100
    all_aligned: bool
    direction: str  # "LONG", "SHORT", "MIXED"
    confidence: str  # "HIGH", "MEDIUM", "LOW"
    
    recommendation: str


class MultiTimeframe:
    """
    Multi-Timeframe Confluence Analysis
    
    Timeframes:
    - 5min: Entry timing
    - 15min: Short-term trend  
    - 1hour: Medium-term trend
    - Daily: Major trend
    
    Rule: Trade only when 3+ timeframes align
    """
    
    TIMEFRAMES = ['5m', '15m', '1h', '1d']
    
    def __init__(self):
        pass
    
    def analyze(self, symbol: str) -> ConfluenceResult:
        """Analyze all timeframes"""
        
        signals = []
        
        for tf in self.TIMEFRAMES:
            sig = self._analyze_timeframe(symbol, tf)
            if sig:
                signals.append(sig)
        
        if not signals:
            return self._neutral_result(symbol)
        
        # Count directions
        bullish = sum(1 for s in signals if s.trend == "BULLISH")
        bearish = sum(1 for s in signals if s.trend == "BEARISH")
        
        # Determine overall direction
        if bullish >= 3:
            direction = "LONG"
            all_aligned = bullish == len(signals)
        elif bearish >= 3:
            direction = "SHORT"
            all_aligned = bearish == len(signals)
        else:
            direction = "MIXED"
            all_aligned = False
        
        # Calculate confluence score
        if all_aligned:
            confluence = 100
            confidence = "HIGH"
        elif bullish >= 3 or bearish >= 3:
            confluence = 75
            confidence = "MEDIUM"
        elif bullish >= 2 or bearish >= 2:
            confluence = 50
            confidence = "LOW"
        else:
            confluence = 25
            confidence = "LOW"
        
        # Recommendation
        if confluence >= 75 and direction != "MIXED":
            rec = f"STRONG_{direction}: All timeframes aligned"
        elif confluence >= 50:
            rec = f"MODERATE_{direction}: Majority aligned"
        else:
            rec = "WAIT: Timeframes conflicting"
        
        return ConfluenceResult(
            symbol=symbol,
            signals=signals,
            confluence_score=confluence,
            all_aligned=all_aligned,
            direction=direction,
            confidence=confidence,
            recommendation=rec
        )
    
    def _analyze_timeframe(self, symbol: str, tf: str) -> Optional[TimeframeSignal]:
        try:
            period = '5d' if tf in ['5m', '15m'] else '3mo'
            df = yf.download(symbol, period=period, interval=tf, progress=False)
            
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if df.empty or len(df) < 20:
                return None
            
            close = df['Close']
            
            # Calculate indicators
            sma20 = close.rolling(20).mean()
            sma50 = close.rolling(50).mean() if len(close) >= 50 else sma20
            
            current = float(close.iloc[-1])
            sma20_val = float(sma20.iloc[-1])
            sma50_val = float(sma50.iloc[-1])
            
            details = []
            
            # Trend determination
            if current > sma20_val > sma50_val:
                trend = "BULLISH"
                strength = 80
                details.append("Price > SMA20 > SMA50")
            elif current < sma20_val < sma50_val:
                trend = "BEARISH"
                strength = 80
                details.append("Price < SMA20 < SMA50")
            elif current > sma20_val:
                trend = "BULLISH"
                strength = 50
                details.append("Price > SMA20")
            elif current < sma20_val:
                trend = "BEARISH"
                strength = 50
                details.append("Price < SMA20")
            else:
                trend = "NEUTRAL"
                strength = 30
            
            return TimeframeSignal(
                timeframe=tf,
                trend=trend,
                strength=strength,
                key_level=sma20_val,
                details=details
            )
            
        except Exception as e:
            logger.debug(f"TF analysis error: {e}")
            return None
    
    def _neutral_result(self, symbol: str) -> ConfluenceResult:
        return ConfluenceResult(symbol, [], 0, False, "MIXED", "LOW", "NO_DATA")


def get_multi_timeframe() -> MultiTimeframe:
    return MultiTimeframe()


if __name__ == "__main__":
    print("Testing MultiTimeframe...")
    mtf = MultiTimeframe()
    
    result = mtf.analyze("AAPL")
    
    print(f"\n{result.symbol} Confluence:")
    print(f"  Score: {result.confluence_score}/100")
    print(f"  Direction: {result.direction}")
    print(f"  Confidence: {result.confidence}")
    print(f"  Aligned: {result.all_aligned}")
    print(f"  Recommendation: {result.recommendation}")
    
    print(f"\nTimeframes:")
    for s in result.signals:
        print(f"  {s.timeframe}: {s.trend} ({s.strength}%)")
