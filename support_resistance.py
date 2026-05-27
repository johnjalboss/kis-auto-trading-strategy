"""
Support/Resistance Analyzer
============================
Identify key price levels for entry/exit optimization.

Methods:
1. Pivot Points (Daily, Weekly)
2. Volume Profile (POC, VAH, VAL)
3. Swing Highs/Lows
4. Round Numbers
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class PriceLevel:
    """Price level (support/resistance)"""
    price: float
    level_type: str  # "SUPPORT", "RESISTANCE"
    strength: int  # 1-5 (number of touches)
    source: str  # "PIVOT", "VOLUME", "SWING", "ROUND"
    description: str


@dataclass
class SRAnalysis:
    """Support/Resistance analysis result"""
    symbol: str
    current_price: float
    
    supports: List[PriceLevel]
    resistances: List[PriceLevel]
    
    nearest_support: Optional[PriceLevel]
    nearest_resistance: Optional[PriceLevel]
    
    pivot_point: float
    r1: float
    r2: float
    s1: float
    s2: float
    
    position_vs_levels: str  # "NEAR_SUPPORT", "NEAR_RESISTANCE", "MID_RANGE"
    risk_reward_score: int  # 0-100


class SupportResistanceAnalyzer:
    """
    Support & Resistance Level Analyzer
    
    Combines multiple methods:
    1. Pivot Points: Classic S1, S2, R1, R2
    2. Volume Profile: High volume nodes
    3. Swing Analysis: Recent swing highs/lows
    4. Round Numbers: Psychological levels
    
    Entry Optimization:
    - Best entry: Near strong support
    - Avoid entry: Near strong resistance
    - Stop loss: Just below support
    """
    
    def __init__(self, lookback: int = 60):
        self.lookback = lookback
    
    def analyze(self, symbol: str) -> SRAnalysis:
        """Analyze support and resistance levels"""
        df = self._fetch_data(symbol)
        
        if df is None or len(df) < 20:
            return self._empty_analysis(symbol)
        
        current_price = df['Close'].iloc[-1]
        
        # Calculate all levels
        pivots = self._calculate_pivots(df)
        swings = self._find_swing_levels(df)
        volume_levels = self._find_volume_levels(df)
        round_levels = self._find_round_numbers(current_price)
        
        # Combine all levels
        all_levels = pivots + swings + volume_levels + round_levels
        
        # Separate into support and resistance
        supports = sorted([l for l in all_levels if l.price < current_price], 
                         key=lambda x: x.price, reverse=True)
        resistances = sorted([l for l in all_levels if l.price > current_price],
                            key=lambda x: x.price)
        
        # Find nearest levels
        nearest_support = supports[0] if supports else None
        nearest_resistance = resistances[0] if resistances else None
        
        # Pivot values
        high = df['High'].iloc[-1]
        low = df['Low'].iloc[-1]
        close = df['Close'].iloc[-1]
        
        pivot = (high + low + close) / 3
        r1 = 2 * pivot - low
        r2 = pivot + (high - low)
        s1 = 2 * pivot - high
        s2 = pivot - (high - low)
        
        # Position analysis
        if nearest_support:
            dist_to_support = (current_price - nearest_support.price) / current_price
        else:
            dist_to_support = 1
        
        if nearest_resistance:
            dist_to_resistance = (nearest_resistance.price - current_price) / current_price
        else:
            dist_to_resistance = 1
        
        if dist_to_support < 0.02:
            position = "NEAR_SUPPORT"
        elif dist_to_resistance < 0.02:
            position = "NEAR_RESISTANCE"
        else:
            position = "MID_RANGE"
        
        # Risk/Reward score
        if dist_to_resistance > 0 and dist_to_support > 0:
            rr_ratio = dist_to_resistance / dist_to_support
            rr_score = min(100, int(rr_ratio * 30))
        else:
            rr_score = 50
        
        return SRAnalysis(
            symbol=symbol,
            current_price=current_price,
            supports=supports[:5],
            resistances=resistances[:5],
            nearest_support=nearest_support,
            nearest_resistance=nearest_resistance,
            pivot_point=pivot,
            r1=r1, r2=r2, s1=s1, s2=s2,
            position_vs_levels=position,
            risk_reward_score=rr_score
        )
    
    def get_optimal_entry(self, symbol: str) -> Tuple[float, float, str]:
        """Get optimal entry price, stop loss, and reason"""
        analysis = self.analyze(symbol)
        
        if analysis.nearest_support:
            entry_price = analysis.nearest_support.price * 1.005  # Slightly above support
            stop_loss = analysis.nearest_support.price * 0.98  # Below support
            reason = f"Entry near {analysis.nearest_support.source} support"
        else:
            entry_price = analysis.current_price
            stop_loss = analysis.current_price * 0.97
            reason = "No strong support found"
        
        return entry_price, stop_loss, reason
    
    def _calculate_pivots(self, df: pd.DataFrame) -> List[PriceLevel]:
        """Calculate pivot points"""
        high = df['High'].iloc[-1]
        low = df['Low'].iloc[-1]
        close = df['Close'].iloc[-1]
        
        pivot = (high + low + close) / 3
        r1 = 2 * pivot - low
        r2 = pivot + (high - low)
        s1 = 2 * pivot - high
        s2 = pivot - (high - low)
        
        levels = [
            PriceLevel(s2, "SUPPORT", 2, "PIVOT", "S2"),
            PriceLevel(s1, "SUPPORT", 3, "PIVOT", "S1"),
            PriceLevel(r1, "RESISTANCE", 3, "PIVOT", "R1"),
            PriceLevel(r2, "RESISTANCE", 2, "PIVOT", "R2"),
        ]
        
        return levels
    
    def _find_swing_levels(self, df: pd.DataFrame, window: int = 5) -> List[PriceLevel]:
        """Find swing highs and lows"""
        levels = []
        
        high = df['High']
        low = df['Low']
        
        for i in range(window, len(df) - window):
            # Swing high
            if high.iloc[i] == high.iloc[i-window:i+window+1].max():
                levels.append(PriceLevel(
                    high.iloc[i], "RESISTANCE", 3, "SWING",
                    f"Swing High {df.index[i].strftime('%m/%d') if hasattr(df.index[i], 'strftime') else ''}"
                ))
            
            # Swing low
            if low.iloc[i] == low.iloc[i-window:i+window+1].min():
                levels.append(PriceLevel(
                    low.iloc[i], "SUPPORT", 3, "SWING",
                    f"Swing Low {df.index[i].strftime('%m/%d') if hasattr(df.index[i], 'strftime') else ''}"
                ))
        
        return levels[-6:]  # Most recent 6 swing points
    
    def _find_volume_levels(self, df: pd.DataFrame) -> List[PriceLevel]:
        """Find high volume price levels (simplified volume profile)"""
        levels = []
        
        # Create price bins
        price_range = df['High'].max() - df['Low'].min()
        num_bins = 20
        bin_size = price_range / num_bins
        
        volume_by_price = {}
        
        for i in range(len(df)):
            price = (df['High'].iloc[i] + df['Low'].iloc[i]) / 2
            volume = df['Volume'].iloc[i]
            bin_price = round(price / bin_size) * bin_size
            
            if bin_price not in volume_by_price:
                volume_by_price[bin_price] = 0
            volume_by_price[bin_price] += volume
        
        # Find high volume nodes (top 3)
        sorted_levels = sorted(volume_by_price.items(), key=lambda x: x[1], reverse=True)
        
        current_price = df['Close'].iloc[-1]
        
        for price, volume in sorted_levels[:3]:
            level_type = "SUPPORT" if price < current_price else "RESISTANCE"
            strength = min(5, int(volume / (df['Volume'].mean() * 3)))
            
            levels.append(PriceLevel(
                price, level_type, strength, "VOLUME",
                "High Volume Node"
            ))
        
        return levels
    
    def _find_round_numbers(self, current_price: float) -> List[PriceLevel]:
        """Find psychological round number levels"""
        levels = []
        
        # Determine round level based on price
        if current_price > 500:
            interval = 50
        elif current_price > 100:
            interval = 25
        elif current_price > 50:
            interval = 10
        elif current_price > 20:
            interval = 5
        else:
            interval = 1
        
        base = round(current_price / interval) * interval
        
        for offset in [-2, -1, 1, 2]:
            level = base + (offset * interval)
            level_type = "SUPPORT" if level < current_price else "RESISTANCE"
            
            levels.append(PriceLevel(
                level, level_type, 2, "ROUND",
                f"Round ${level}"
            ))
        
        return levels
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch price data"""
        try:
            df = yf.download(symbol, period=f'{self.lookback}d', progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return None
    
    def _empty_analysis(self, symbol: str) -> SRAnalysis:
        """Return empty analysis"""
        return SRAnalysis(
            symbol=symbol, current_price=0,
            supports=[], resistances=[],
            nearest_support=None, nearest_resistance=None,
            pivot_point=0, r1=0, r2=0, s1=0, s2=0,
            position_vs_levels="UNKNOWN", risk_reward_score=0
        )


# Global instance
_analyzer = None

def get_sr_analyzer() -> SupportResistanceAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = SupportResistanceAnalyzer()
    return _analyzer


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing SupportResistanceAnalyzer...")
    
    analyzer = SupportResistanceAnalyzer()
    
    for symbol in ["AAPL", "NVDA", "TSLA"]:
        print(f"\n{'='*50}")
        print(f"{symbol}")
        print('='*50)
        
        result = analyzer.analyze(symbol)
        
        print(f"Current: ${result.current_price:.2f}")
        print(f"Position: {result.position_vs_levels}")
        print(f"R/R Score: {result.risk_reward_score}")
        print()
        print(f"Pivot: ${result.pivot_point:.2f}")
        print(f"R1: ${result.r1:.2f} | R2: ${result.r2:.2f}")
        print(f"S1: ${result.s1:.2f} | S2: ${result.s2:.2f}")
        
        if result.nearest_support:
            print(f"\nNearest Support: ${result.nearest_support.price:.2f} ({result.nearest_support.source})")
        if result.nearest_resistance:
            print(f"Nearest Resistance: ${result.nearest_resistance.price:.2f} ({result.nearest_resistance.source})")
