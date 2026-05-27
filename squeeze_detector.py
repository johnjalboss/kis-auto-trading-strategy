"""
Squeeze Detector
=================
Detect short squeeze and gamma squeeze potential.

Metrics:
1. Short Interest %
2. Days to Cover
3. Cost to Borrow
4. Options Gamma Exposure
5. Volume Surge Detection
"""

from dataclasses import dataclass
from typing import Optional, List, Dict
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class SqueezeSignal:
    """Squeeze analysis result"""
    symbol: str
    
    # Short squeeze metrics
    short_interest_pct: float  # % of float
    days_to_cover: float
    short_change_weekly: float  # % change in SI
    
    # Volume analysis
    volume_surge: bool
    volume_ratio: float
    
    # Price action
    is_breaking_resistance: bool
    price_vs_sma20: float  # % above/below
    consecutive_up_days: int
    
    # Squeeze potential
    short_squeeze_score: int  # 0-100
    gamma_squeeze_score: int  # 0-100
    total_score: int
    
    squeeze_type: str  # "SHORT_SQUEEZE", "GAMMA_SQUEEZE", "BOTH", "NONE"
    signal: str
    details: List[str]


class SqueezeDetector:
    """
    Short Squeeze & Gamma Squeeze Detector
    
    Short Squeeze Conditions:
    1. High short interest (>15% of float)
    2. Days to cover > 3
    3. Price breaking above resistance
    4. Volume surge (>2x average)
    5. Consecutive up days
    
    Gamma Squeeze Conditions:
    1. Large call open interest near the money
    2. Stock approaching call strike prices
    3. Dealers forced to buy stock to hedge
    4. Rapid price acceleration
    
    WARNING: High risk trades - use with caution!
    """
    
    def __init__(self):
        self._cache: Dict[str, dict] = {}
    
    def analyze(self, symbol: str) -> SqueezeSignal:
        """Analyze squeeze potential"""
        details = []
        short_score = 0
        gamma_score = 0
        
        # Fetch data
        df = self._fetch_price_data(symbol)
        info = self._fetch_info(symbol)
        
        if df is None or len(df) < 20:
            return self._no_squeeze_result(symbol)
        
        close = df['Close']
        volume = df['Volume']
        
        # 1. Short interest analysis
        shares_short = info.get('sharesShort', 0) or 0
        float_shares = info.get('floatShares', 0) or info.get('sharesOutstanding', 1) or 1
        
        short_interest_pct = (shares_short / float_shares) if float_shares > 0 else 0
        
        # Days to cover
        avg_volume = volume.tail(20).mean()
        days_to_cover = shares_short / avg_volume if avg_volume > 0 else 0
        
        # Short interest scoring
        if short_interest_pct > 0.30:
            short_score += 40
            details.append(f"SI:{short_interest_pct:.0%}(EXTREME)")
        elif short_interest_pct > 0.20:
            short_score += 30
            details.append(f"SI:{short_interest_pct:.0%}(HIGH)")
        elif short_interest_pct > 0.15:
            short_score += 20
            details.append(f"SI:{short_interest_pct:.0%}")
        elif short_interest_pct > 0.10:
            short_score += 10
        
        # Days to cover scoring
        if days_to_cover > 5:
            short_score += 25
            details.append(f"DTC:{days_to_cover:.1f}(LONG)")
        elif days_to_cover > 3:
            short_score += 15
            details.append(f"DTC:{days_to_cover:.1f}")
        
        # 2. Volume surge
        recent_vol = volume.iloc[-1]
        vol_ratio = recent_vol / avg_volume if avg_volume > 0 else 1
        volume_surge = vol_ratio > 2.0
        
        if volume_surge:
            short_score += 15
            gamma_score += 15
            details.append(f"VOL:{vol_ratio:.1f}x(SURGE)")
        elif vol_ratio > 1.5:
            short_score += 10
            gamma_score += 10
        
        # 3. Price breaking resistance
        high_20 = close.tail(20).max()
        current = close.iloc[-1]
        is_breaking = current >= high_20 * 0.98
        
        if is_breaking:
            short_score += 15
            gamma_score += 20
            details.append("BREAKING_RESISTANCE")
        
        # 4. Price vs SMA
        sma20 = close.rolling(20).mean().iloc[-1]
        price_vs_sma = (current / sma20 - 1) if sma20 > 0 else 0
        
        if price_vs_sma > 0.10:
            short_score += 10
            gamma_score += 15
            details.append(f"ABOVE_SMA:{price_vs_sma:.0%}")
        elif price_vs_sma > 0.05:
            short_score += 5
        
        # 5. Consecutive up days
        consecutive = self._count_consecutive_up(df)
        
        if consecutive >= 5:
            short_score += 15
            gamma_score += 10
            details.append(f"UP_DAYS:{consecutive}")
        elif consecutive >= 3:
            short_score += 10
        
        # 6. Rapid price acceleration (gamma indicator)
        price_change_3d = (current / close.iloc[-4] - 1) if len(close) > 4 else 0
        
        if price_change_3d > 0.15:
            gamma_score += 30
            details.append(f"ACCELERATION:{price_change_3d:.0%}")
        elif price_change_3d > 0.08:
            gamma_score += 20
        
        # Short change (if available)
        short_change = 0  # Would need historical SI data
        
        # Determine squeeze type
        total_score = (short_score + gamma_score) // 2
        
        if short_score >= 60 and gamma_score >= 60:
            squeeze_type = "BOTH"
            signal = "🚀 EXTREME_SQUEEZE_POTENTIAL"
        elif short_score >= 50:
            squeeze_type = "SHORT_SQUEEZE"
            signal = "📈 SHORT_SQUEEZE_POTENTIAL"
        elif gamma_score >= 50:
            squeeze_type = "GAMMA_SQUEEZE"
            signal = "🎰 GAMMA_SQUEEZE_POTENTIAL"
        else:
            squeeze_type = "NONE"
            signal = "NO_SQUEEZE"
        
        return SqueezeSignal(
            symbol=symbol,
            short_interest_pct=short_interest_pct,
            days_to_cover=days_to_cover,
            short_change_weekly=short_change,
            volume_surge=volume_surge,
            volume_ratio=vol_ratio,
            is_breaking_resistance=is_breaking,
            price_vs_sma20=price_vs_sma,
            consecutive_up_days=consecutive,
            short_squeeze_score=min(100, short_score),
            gamma_squeeze_score=min(100, gamma_score),
            total_score=min(100, total_score),
            squeeze_type=squeeze_type,
            signal=signal,
            details=details
        )
    
    def _count_consecutive_up(self, df: pd.DataFrame) -> int:
        """Count consecutive up days"""
        close = df['Close']
        count = 0
        
        for i in range(len(close) - 1, 0, -1):
            if close.iloc[i] > close.iloc[i-1]:
                count += 1
            else:
                break
        
        return count
    
    def _fetch_price_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch price data"""
        try:
            df = yf.download(symbol, period='60d', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return None
    
    def _fetch_info(self, symbol: str) -> dict:
        """Fetch stock info"""
        try:
            ticker = yf.Ticker(symbol)
            return ticker.info or {}
        except:
            return {}
    
    def _no_squeeze_result(self, symbol: str) -> SqueezeSignal:
        """Return no squeeze result"""
        return SqueezeSignal(
            symbol=symbol, short_interest_pct=0, days_to_cover=0,
            short_change_weekly=0, volume_surge=False, volume_ratio=1,
            is_breaking_resistance=False, price_vs_sma20=0, consecutive_up_days=0,
            short_squeeze_score=0, gamma_squeeze_score=0, total_score=0,
            squeeze_type="NONE", signal="NO_SQUEEZE", details=[]
        )


# Global instance
_detector = None

def get_squeeze_detector() -> SqueezeDetector:
    global _detector
    if _detector is None:
        _detector = SqueezeDetector()
    return _detector


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing SqueezeDetector...")
    
    detector = SqueezeDetector()
    
    # Test some known high SI stocks
    test_symbols = ["GME", "AMC", "TSLA", "NVDA"]
    
    for symbol in test_symbols:
        print(f"\n{'='*50}")
        print(f"{symbol}")
        print('='*50)
        
        result = detector.analyze(symbol)
        
        print(f"Signal: {result.signal}")
        print(f"Type: {result.squeeze_type}")
        print(f"Short Score: {result.short_squeeze_score}")
        print(f"Gamma Score: {result.gamma_squeeze_score}")
        print(f"SI: {result.short_interest_pct:.1%}")
        print(f"DTC: {result.days_to_cover:.1f} days")
        print(f"Vol Ratio: {result.volume_ratio:.1f}x")
        print(f"Up Days: {result.consecutive_up_days}")
        print(f"Details: {result.details}")
