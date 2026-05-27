"""
Volume Profile Analyzer
=========================
Analyze volume distribution at price levels.

Metrics:
1. Point of Control (POC) - Highest volume price
2. Value Area (70% of volume)
3. High Volume Nodes (HVN)
4. Low Volume Nodes (LVN)
"""

from dataclasses import dataclass
from typing import Optional, List, Dict
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class VolumeNode:
    """Volume node at price level"""
    price_level: float
    volume: float
    volume_pct: float
    node_type: str  # "HVN", "LVN", "NORMAL"


@dataclass
class VolumeProfileSignal:
    """Volume profile analysis"""
    symbol: str
    current_price: float
    
    # Key levels
    poc: float                 # Point of Control
    value_area_high: float     # VAH - 70% of volume
    value_area_low: float      # VAL
    
    # Position relative to profile
    above_poc: bool
    in_value_area: bool
    
    # Volume nodes
    hvn_levels: List[float]    # High Volume Nodes (support/resistance)
    lvn_levels: List[float]    # Low Volume Nodes (breakout zones)
    
    # Analysis
    nearest_hvn: float
    nearest_lvn: float
    
    # Scoring
    volume_profile_score: int  # -100 to +100
    signal: str
    details: List[str]


class VolumeProfileAnalyzer:
    """
    Volume Profile Analysis
    
    Key Concepts:
    - POC = Fair value, price tends to return here
    - VAH/VAL = 70% of volume traded, key S/R
    - HVN = Acceptance zones, price congests here
    - LVN = Rejection zones, fast moves through
    
    Strategy:
    - Price below VAL → Look for longs (value)
    - Price above VAH → Caution (extended)
    - Near LVN → Expect fast move
    - Return to POC → Mean reversion
    
    Scoring:
    - Price below VAL: +30 (undervalued)
    - Near POC from below: +20 (reversion trade)
    - Price above VAH: -15 (extended)
    - At LVN: +15 (breakout potential)
    """
    
    def __init__(self, num_bins: int = 30, lookback: int = 60):
        self.num_bins = num_bins
        self.lookback = lookback
    
    def analyze(self, symbol: str) -> VolumeProfileSignal:
        """Build volume profile and analyze"""
        details = []
        score = 0
        
        df = self._fetch_data(symbol)
        
        if df is None or len(df) < 20:
            return self._neutral_result(symbol)
        
        close = df['Close']
        volume = df['Volume']
        high = df['High']
        low = df['Low']
        
        current = close.iloc[-1]
        
        # Build volume profile
        profile = self._build_profile(df)
        
        if not profile:
            return self._neutral_result(symbol)
        
        # Find POC (highest volume level)
        poc_level = max(profile, key=lambda x: x.volume)
        poc = poc_level.price_level
        
        # Calculate Value Area (70% of total volume)
        total_vol = sum(p.volume for p in profile)
        sorted_profile = sorted(profile, key=lambda x: x.volume, reverse=True)
        
        va_vol = 0
        va_levels = []
        for p in sorted_profile:
            va_vol += p.volume
            va_levels.append(p.price_level)
            if va_vol >= total_vol * 0.7:
                break
        
        vah = max(va_levels) if va_levels else current * 1.05
        val = min(va_levels) if va_levels else current * 0.95
        
        # Find HVN and LVN
        avg_vol = total_vol / len(profile) if profile else 0
        hvn_levels = [p.price_level for p in profile if p.volume > avg_vol * 1.5]
        lvn_levels = [p.price_level for p in profile if p.volume < avg_vol * 0.5]
        
        # Position analysis
        above_poc = current > poc
        in_va = val <= current <= vah
        
        # Scoring
        if current < val:
            score += 30
            details.append("BELOW_VALUE_AREA:Undervalued")
        elif current > vah:
            score -= 15
            details.append("ABOVE_VALUE_AREA:Extended")
        
        if in_va:
            details.append("IN_VALUE_AREA")
        
        # Distance to POC
        poc_dist = (current - poc) / poc
        if -0.02 < poc_dist < 0:
            score += 20
            details.append("NEAR_POC_FROM_BELOW")
        elif 0 < poc_dist < 0.02:
            score -= 10
            details.append("NEAR_POC_FROM_ABOVE")
        
        # LVN proximity (breakout potential)
        nearest_lvn = min(lvn_levels, key=lambda x: abs(x - current)) if lvn_levels else current
        if abs(current - nearest_lvn) / current < 0.02:
            score += 15
            details.append("AT_LVN:Breakout_Zone")
        
        # HVN proximity
        nearest_hvn = min(hvn_levels, key=lambda x: abs(x - current)) if hvn_levels else poc
        
        # Signal
        if score >= 30:
            signal = "VP_BULLISH"
        elif score >= 10:
            signal = "VP_SLIGHTLY_BULLISH"
        elif score <= -25:
            signal = "VP_BEARISH"
        elif score <= -10:
            signal = "VP_SLIGHTLY_BEARISH"
        else:
            signal = "VP_NEUTRAL"
        
        return VolumeProfileSignal(
            symbol=symbol,
            current_price=current,
            poc=poc,
            value_area_high=vah,
            value_area_low=val,
            above_poc=above_poc,
            in_value_area=in_va,
            hvn_levels=hvn_levels[:5],
            lvn_levels=lvn_levels[:5],
            nearest_hvn=nearest_hvn,
            nearest_lvn=nearest_lvn,
            volume_profile_score=max(-100, min(100, score)),
            signal=signal,
            details=details
        )
    
    def _build_profile(self, df: pd.DataFrame) -> List[VolumeNode]:
        """Build volume profile"""
        high = df['High']
        low = df['Low']
        close = df['Close']
        volume = df['Volume']
        
        # Price range
        price_high = high.max()
        price_low = low.min()
        
        if price_high == price_low:
            return []
        
        # Create bins
        bin_size = (price_high - price_low) / self.num_bins
        bins = []
        
        for i in range(self.num_bins):
            bin_low = price_low + i * bin_size
            bin_high = bin_low + bin_size
            bin_mid = (bin_low + bin_high) / 2
            
            # Volume in this price bin (simplified)
            mask = (low <= bin_high) & (high >= bin_low)
            bin_volume = volume[mask].sum()
            
            bins.append({
                'price': bin_mid,
                'volume': bin_volume
            })
        
        # Calculate percentages and classify nodes
        total_vol = sum(b['volume'] for b in bins)
        avg_vol = total_vol / len(bins) if bins else 0
        
        profile = []
        for b in bins:
            vol_pct = (b['volume'] / total_vol * 100) if total_vol > 0 else 0
            
            if b['volume'] > avg_vol * 1.5:
                node_type = "HVN"
            elif b['volume'] < avg_vol * 0.5:
                node_type = "LVN"
            else:
                node_type = "NORMAL"
            
            profile.append(VolumeNode(
                price_level=b['price'],
                volume=b['volume'],
                volume_pct=vol_pct,
                node_type=node_type
            ))
        
        return profile
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch data"""
        try:
            df = yf.download(symbol, period=f'{self.lookback}d', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return None
    
    def _neutral_result(self, symbol: str) -> VolumeProfileSignal:
        """Return neutral"""
        return VolumeProfileSignal(
            symbol=symbol, current_price=0, poc=0, value_area_high=0,
            value_area_low=0, above_poc=False, in_value_area=False,
            hvn_levels=[], lvn_levels=[], nearest_hvn=0, nearest_lvn=0,
            volume_profile_score=0, signal="NO_DATA", details=[]
        )


# Global
_analyzer = None

def get_volume_profile_analyzer() -> VolumeProfileAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = VolumeProfileAnalyzer()
    return _analyzer


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing VolumeProfileAnalyzer...")
    
    analyzer = VolumeProfileAnalyzer()
    
    for symbol in ["AAPL", "NVDA"]:
        print(f"\n{'='*50}")
        print(f"{symbol}")
        print('='*50)
        
        result = analyzer.analyze(symbol)
        
        print(f"Current: ${result.current_price:.2f}")
        print(f"Signal: {result.signal} ({result.volume_profile_score:+d})")
        print()
        print(f"POC: ${result.poc:.2f}")
        print(f"Value Area: ${result.value_area_low:.2f} - ${result.value_area_high:.2f}")
        print(f"In Value Area: {result.in_value_area}")
        print(f"Above POC: {result.above_poc}")
        print()
        print(f"HVN Levels: {[f'${x:.2f}' for x in result.hvn_levels[:3]]}")
        print(f"LVN Levels: {[f'${x:.2f}' for x in result.lvn_levels[:3]]}")
        print(f"Details: {result.details}")
