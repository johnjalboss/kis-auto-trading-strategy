"""
Fibonacci Levels Analyzer
===========================
Calculate and analyze Fibonacci retracement/extension levels.

Levels:
1. Retracement: 23.6%, 38.2%, 50%, 61.8%, 78.6%
2. Extension: 127.2%, 161.8%, 200%, 261.8%
"""

from dataclasses import dataclass
from typing import Optional, List, Dict
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class FibLevel:
    """Fibonacci level"""
    ratio: float
    price: float
    level_type: str  # "support", "resistance"
    strength: int    # 1-3


@dataclass
class FibonacciSignal:
    """Fibonacci analysis result"""
    symbol: str
    current_price: float
    
    # Swing points
    swing_high: float
    swing_low: float
    trend: str  # "UP", "DOWN"
    
    # Key levels
    levels: List[FibLevel]
    
    # Current position
    nearest_support: float
    nearest_resistance: float
    distance_to_support_pct: float
    distance_to_resistance_pct: float
    
    # At key level?
    at_fib_level: bool
    fib_level_type: str  # "SUPPORT", "RESISTANCE", "NONE"
    
    # Scoring
    fib_score: int  # -100 to +100
    signal: str
    details: List[str]


class FibonacciAnalyzer:
    """
    Fibonacci Retracement & Extension Analysis
    
    Key Levels:
    - 38.2% - Shallow retracement (strong trend)
    - 50.0% - Psychological level
    - 61.8% - Golden ratio (key reversal zone)
    - 78.6% - Deep retracement
    
    Scoring:
    - Price at 61.8% support: +35
    - Price at 38.2% support: +25
    - Price at 61.8% resistance: -25
    - Bouncing from Fib level: +20
    """
    
    # Fibonacci ratios
    RETRACEMENT_RATIOS = [0.236, 0.382, 0.500, 0.618, 0.786]
    EXTENSION_RATIOS = [1.272, 1.618, 2.000, 2.618]
    
    def __init__(self, lookback: int = 60):
        self.lookback = lookback
    
    def analyze(self, symbol: str) -> FibonacciSignal:
        """Analyze Fibonacci levels"""
        details = []
        score = 0
        
        df = self._fetch_data(symbol)
        
        if df is None or len(df) < 20:
            return self._neutral_result(symbol)
        
        close = df['Close']
        high = df['High']
        low = df['Low']
        current = close.iloc[-1]
        
        # Find swing high and low
        swing_high = high.max()
        swing_low = low.min()
        
        # Determine trend (for retracement direction)
        mid_point = len(df) // 2
        first_half_avg = close.iloc[:mid_point].mean()
        second_half_avg = close.iloc[mid_point:].mean()
        
        if second_half_avg > first_half_avg:
            trend = "UP"
            # In uptrend, calculate retracements from high to low
            fib_range = swing_high - swing_low
            levels = self._calculate_levels(swing_low, swing_high, fib_range, "UP")
        else:
            trend = "DOWN"
            fib_range = swing_high - swing_low
            levels = self._calculate_levels(swing_low, swing_high, fib_range, "DOWN")
        
        # Find nearest support/resistance
        supports = [l for l in levels if l.price < current]
        resistances = [l for l in levels if l.price > current]
        
        nearest_support = max([l.price for l in supports]) if supports else swing_low
        nearest_resistance = min([l.price for l in resistances]) if resistances else swing_high
        
        dist_to_support = (current - nearest_support) / current * 100
        dist_to_resistance = (nearest_resistance - current) / current * 100
        
        # Check if at Fib level (within 1%)
        at_level = False
        level_type = "NONE"
        
        for level in levels:
            distance = abs(current - level.price) / current
            
            if distance < 0.01:  # Within 1%
                at_level = True
                level_type = level.level_type.upper()
                
                if level.ratio == 0.618:
                    if level_type == "SUPPORT":
                        score += 35
                        details.append(f"AT_61.8%_SUPPORT:${level.price:.2f}")
                    else:
                        score -= 25
                        details.append(f"AT_61.8%_RESISTANCE:${level.price:.2f}")
                elif level.ratio == 0.382:
                    if level_type == "SUPPORT":
                        score += 25
                        details.append(f"AT_38.2%_SUPPORT:${level.price:.2f}")
                    else:
                        score -= 15
                elif level.ratio == 0.500:
                    if level_type == "SUPPORT":
                        score += 20
                        details.append(f"AT_50%_SUPPORT:${level.price:.2f}")
                break
        
        # Extra score if bouncing from level
        if at_level and close.iloc[-1] > close.iloc[-2]:
            score += 15
            details.append("BOUNCING_FROM_FIB")
        
        # Risk/Reward based on Fib levels
        if dist_to_support < 3 and dist_to_resistance > 5:
            score += 15
            details.append(f"GOOD_RR:{dist_to_resistance/dist_to_support:.1f}")
        elif dist_to_resistance < 2 and dist_to_support > 5:
            score -= 15
            details.append("POOR_RR:Near_Resistance")
        
        # Signal
        if score >= 30:
            signal = "FIB_BUY"
        elif score >= 10:
            signal = "FIB_HOLD"
        elif score <= -30:
            signal = "FIB_CAUTION"
        elif score <= -10:
            signal = "FIB_RESISTANCE"
        else:
            signal = "FIB_NEUTRAL"
        
        return FibonacciSignal(
            symbol=symbol,
            current_price=current,
            swing_high=swing_high,
            swing_low=swing_low,
            trend=trend,
            levels=levels,
            nearest_support=nearest_support,
            nearest_resistance=nearest_resistance,
            distance_to_support_pct=dist_to_support,
            distance_to_resistance_pct=dist_to_resistance,
            at_fib_level=at_level,
            fib_level_type=level_type,
            fib_score=max(-100, min(100, score)),
            signal=signal,
            details=details
        )
    
    def _calculate_levels(self, low: float, high: float, 
                          fib_range: float, trend: str) -> List[FibLevel]:
        """Calculate Fibonacci levels"""
        levels = []
        
        for ratio in self.RETRACEMENT_RATIOS:
            if trend == "UP":
                # Retracement from high
                price = high - (fib_range * ratio)
                level_type = "support"
            else:
                # Retracement from low
                price = low + (fib_range * ratio)
                level_type = "resistance"
            
            strength = 3 if ratio in [0.618, 0.500] else (2 if ratio == 0.382 else 1)
            
            levels.append(FibLevel(
                ratio=ratio,
                price=price,
                level_type=level_type,
                strength=strength
            ))
        
        # Extensions
        for ratio in self.EXTENSION_RATIOS:
            if trend == "UP":
                price = high + (fib_range * (ratio - 1))
                level_type = "resistance"
            else:
                price = low - (fib_range * (ratio - 1))
                level_type = "support"
            
            strength = 3 if ratio == 1.618 else 2
            
            levels.append(FibLevel(
                ratio=ratio,
                price=price,
                level_type=level_type,
                strength=strength
            ))
        
        return sorted(levels, key=lambda x: x.price)
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch data"""
        try:
            df = yf.download(symbol, period=f'{self.lookback}d', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return None
    
    def _neutral_result(self, symbol: str) -> FibonacciSignal:
        """Return neutral"""
        return FibonacciSignal(
            symbol=symbol, current_price=0, swing_high=0, swing_low=0,
            trend="UNKNOWN", levels=[], nearest_support=0, nearest_resistance=0,
            distance_to_support_pct=0, distance_to_resistance_pct=0,
            at_fib_level=False, fib_level_type="NONE",
            fib_score=0, signal="UNKNOWN", details=[]
        )


# Global
_analyzer = None

def get_fibonacci_analyzer() -> FibonacciAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = FibonacciAnalyzer()
    return _analyzer


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing FibonacciAnalyzer...")
    
    analyzer = FibonacciAnalyzer()
    
    for symbol in ["AAPL", "NVDA"]:
        print(f"\n{'='*50}")
        print(f"{symbol}")
        print('='*50)
        
        result = analyzer.analyze(symbol)
        
        print(f"Current: ${result.current_price:.2f}")
        print(f"Swing: ${result.swing_low:.2f} - ${result.swing_high:.2f}")
        print(f"Trend: {result.trend}")
        print()
        print(f"Signal: {result.signal} ({result.fib_score:+d})")
        print(f"At Fib Level: {result.at_fib_level} ({result.fib_level_type})")
        print(f"Nearest Support: ${result.nearest_support:.2f} ({result.distance_to_support_pct:.1f}%)")
        print(f"Nearest Resistance: ${result.nearest_resistance:.2f} ({result.distance_to_resistance_pct:.1f}%)")
        print()
        print("Key Levels:")
        for l in result.levels:
            if l.strength >= 2:
                print(f"  {l.ratio:.1%}: ${l.price:.2f} ({l.level_type})")
        print(f"Details: {result.details}")
