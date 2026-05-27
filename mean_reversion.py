"""
Mean Reversion Detector
=========================
Detect overextended moves likely to reverse.
"""

from dataclasses import dataclass
from typing import Optional
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class MeanReversionSignal:
    symbol: str
    is_extended: bool
    direction: str  # "OVERSOLD", "OVERBOUGHT", "NEUTRAL"
    
    # Metrics
    rsi: float
    bb_percentile: float  # 0-100, position in Bollinger Bands
    distance_from_mean_pct: float
    zscore: float
    
    # Signal
    reversion_probability: float
    expected_move_pct: float
    
    signal_strength: str  # "STRONG", "MODERATE", "WEAK"
    recommended_action: str


class MeanReversionDetector:
    """
    Mean Reversion Strategy
    
    Indicators:
    1. RSI extremes (<25 or >75)
    2. Bollinger Band extremes
    3. Z-Score from 20-day mean
    4. Distance from moving averages
    
    Best for: Range-bound markets
    Avoid: Strong trending markets
    """
    
    def __init__(self):
        pass
    
    def analyze(self, symbol: str) -> MeanReversionSignal:
        """Analyze for mean reversion opportunity"""
        
        try:
            df = yf.download(symbol, period='3mo', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if df.empty or len(df) < 30:
                return self._neutral(symbol)
            
            close = df['Close']
            current = float(close.iloc[-1])
            
            # RSI
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss.replace(0, 1)
            rsi = 100 - (100 / (1 + rs))
            rsi_val = float(rsi.iloc[-1])
            
            # Bollinger Bands
            sma20 = close.rolling(20).mean()
            std20 = close.rolling(20).std()
            upper = sma20 + 2 * std20
            lower = sma20 - 2 * std20
            
            bb_range = float(upper.iloc[-1] - lower.iloc[-1])
            bb_pos = (current - float(lower.iloc[-1])) / bb_range * 100 if bb_range > 0 else 50
            
            # Z-Score
            mean20 = float(sma20.iloc[-1])
            std_val = float(std20.iloc[-1])
            zscore = (current - mean20) / std_val if std_val > 0 else 0
            
            # Distance from mean
            distance = (current - mean20) / mean20 * 100
            
            # Determine if extended
            oversold = rsi_val < 25 or bb_pos < 5 or zscore < -2
            overbought = rsi_val > 75 or bb_pos > 95 or zscore > 2
            
            if oversold:
                direction = "OVERSOLD"
                prob = 0.70 if rsi_val < 20 else 0.60
                expected = abs(distance) * 0.5  # Expect 50% reversion
                action = f"LONG: Oversold, expect +{expected:.1f}% bounce"
            elif overbought:
                direction = "OVERBOUGHT"
                prob = 0.65 if rsi_val > 80 else 0.55
                expected = abs(distance) * 0.5
                action = f"AVOID LONG: Overbought, expect -{expected:.1f}% pullback"
            else:
                direction = "NEUTRAL"
                prob = 0.50
                expected = 0
                action = "No mean reversion setup"
            
            # Signal strength
            extreme_count = sum([
                rsi_val < 25 or rsi_val > 75,
                bb_pos < 10 or bb_pos > 90,
                abs(zscore) > 2
            ])
            
            if extreme_count >= 3:
                strength = "STRONG"
            elif extreme_count >= 2:
                strength = "MODERATE"
            else:
                strength = "WEAK"
            
            return MeanReversionSignal(
                symbol=symbol,
                is_extended=oversold or overbought,
                direction=direction,
                rsi=rsi_val,
                bb_percentile=bb_pos,
                distance_from_mean_pct=distance,
                zscore=zscore,
                reversion_probability=prob,
                expected_move_pct=expected,
                signal_strength=strength,
                recommended_action=action
            )
            
        except Exception as e:
            logger.debug(f"Mean reversion error: {e}")
            return self._neutral(symbol)
    
    def _neutral(self, symbol: str) -> MeanReversionSignal:
        return MeanReversionSignal(symbol, False, "NEUTRAL", 50, 50, 0, 0, 0.5, 0, "WEAK", "No data")


def get_mean_reversion() -> MeanReversionDetector:
    return MeanReversionDetector()


if __name__ == "__main__":
    print("Testing MeanReversionDetector...")
    mr = MeanReversionDetector()
    
    for sym in ["AAPL", "NVDA", "TSLA"]:
        sig = mr.analyze(sym)
        print(f"\n{sym}:")
        print(f"  Direction: {sig.direction}")
        print(f"  RSI: {sig.rsi:.1f}")
        print(f"  BB%: {sig.bb_percentile:.1f}%")
        print(f"  Z-Score: {sig.zscore:.2f}")
        print(f"  Strength: {sig.signal_strength}")
        print(f"  Action: {sig.recommended_action}")
