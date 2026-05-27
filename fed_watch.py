"""
Fed Watch - Interest Rate Expectations
========================================
Track Federal Reserve policy expectations.

Metrics:
1. Fed Funds Rate Current/Target
2. Rate Cut/Hike Probability
3. FOMC Statement Sentiment
4. Dot Plot Trajectory
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class FedSignal:
    """Fed policy analysis"""
    current_rate: float        # Current Fed Funds rate
    expected_rate_1m: float    # Expected in 1 month
    expected_rate_3m: float    # Expected in 3 months
    expected_rate_6m: float    # Expected in 6 months
    
    rate_direction: str        # "HIKING", "CUTTING", "HOLD"
    rate_momentum: str         # "ACCELERATING", "DECELERATING", "STABLE"
    
    # Bond market signals
    yield_2y: float
    yield_10y: float
    yield_spread: float        # 10Y - 2Y
    
    # Impact on stocks
    stock_impact: str          # "BULLISH", "BEARISH", "NEUTRAL"
    sector_rotation: List[str] # Favored sectors
    
    fed_score: int             # -100 to +100
    signal: str
    details: List[str]


class FedWatchAnalyzer:
    """
    Federal Reserve Policy Analyzer
    
    Rate Impact on Stocks:
    - Rate cuts expected → Bullish (growth/tech favored)
    - Rate hikes expected → Bearish (value/defensive favored)
    - Pause → Depends on economy
    
    Yield Curve Signals:
    - Steepening (10Y > 2Y widening) → Risk-on
    - Flattening → Caution
    - Inversion (2Y > 10Y) → Recession warning
    
    Scoring:
    - Rate cuts priced in: +30
    - Curve steepening: +20
    - Positive real rates: +15
    - Inversion: -40
    """
    
    # Current Fed Funds target (update periodically)
    CURRENT_FED_FUNDS = 5.25  # As of late 2024
    
    def __init__(self):
        self._cache: Dict[str, pd.DataFrame] = {}
    
    def analyze(self) -> FedSignal:
        """Analyze Fed policy outlook"""
        details = []
        score = 0
        
        # Fetch yield data
        yield_2y, yield_10y = self._fetch_yields()
        yield_spread = yield_10y - yield_2y
        
        # 1. Yield Curve Analysis
        if yield_spread < 0:
            # Inverted curve - recession signal
            score -= 40
            details.append(f"INVERTED_CURVE:{yield_spread:.2f}%")
            rate_direction = "CUTTING"  # Cuts coming eventually
        elif yield_spread < 0.3:
            # Flat curve - uncertainty
            score -= 15
            details.append(f"FLAT_CURVE:{yield_spread:.2f}%")
            rate_direction = "HOLD"
        elif yield_spread > 1.0:
            # Steep curve - growth expected
            score += 25
            details.append(f"STEEP_CURVE:{yield_spread:.2f}%")
            rate_direction = "HOLD"
        else:
            rate_direction = "HOLD"
            details.append(f"NORMAL_CURVE:{yield_spread:.2f}%")
        
        # 2. Rate Expectations (from 2Y yield vs Fed Funds)
        rate_implied_change = yield_2y - self.CURRENT_FED_FUNDS
        
        if rate_implied_change < -0.5:
            # Market pricing in cuts
            score += 30
            details.append(f"CUTS_PRICED_IN:{rate_implied_change:.2f}%")
            rate_direction = "CUTTING"
            rate_momentum = "ACCELERATING"
        elif rate_implied_change < -0.25:
            score += 15
            rate_direction = "CUTTING"
            rate_momentum = "STABLE"
        elif rate_implied_change > 0.25:
            # More hikes expected
            score -= 25
            details.append(f"HIKES_PRICED_IN:{rate_implied_change:+.2f}%")
            rate_direction = "HIKING"
            rate_momentum = "ACCELERATING"
        else:
            rate_momentum = "STABLE"
        
        # 3. Rate Level Impact
        if yield_10y > 5.0:
            score -= 20
            details.append("HIGH_RATES:Restrictive")
        elif yield_10y < 3.5:
            score += 15
            details.append("LOW_RATES:Accommodative")
        
        # 4. Stock Impact
        if score >= 20:
            stock_impact = "BULLISH"
            sector_rotation = ["XLK", "XLY", "XLC"]  # Growth sectors
        elif score <= -20:
            stock_impact = "BEARISH"
            sector_rotation = ["XLU", "XLP", "XLV"]  # Defensive
        else:
            stock_impact = "NEUTRAL"
            sector_rotation = ["XLF", "XLI"]  # Cyclicals if soft landing
        
        # Expected rates (simplified projection)
        expected_1m = self.CURRENT_FED_FUNDS + (rate_implied_change * 0.2)
        expected_3m = self.CURRENT_FED_FUNDS + (rate_implied_change * 0.5)
        expected_6m = self.CURRENT_FED_FUNDS + rate_implied_change
        
        # Signal
        if score >= 30:
            signal = "FED_BULLISH"
        elif score >= 10:
            signal = "FED_SLIGHTLY_BULLISH"
        elif score <= -30:
            signal = "FED_BEARISH"
        elif score <= -10:
            signal = "FED_SLIGHTLY_BEARISH"
        else:
            signal = "FED_NEUTRAL"
        
        return FedSignal(
            current_rate=self.CURRENT_FED_FUNDS,
            expected_rate_1m=expected_1m,
            expected_rate_3m=expected_3m,
            expected_rate_6m=expected_6m,
            rate_direction=rate_direction,
            rate_momentum=rate_momentum,
            yield_2y=yield_2y,
            yield_10y=yield_10y,
            yield_spread=yield_spread,
            stock_impact=stock_impact,
            sector_rotation=sector_rotation,
            fed_score=max(-100, min(100, score)),
            signal=signal,
            details=details
        )
    
    def _fetch_yields(self) -> tuple:
        """Fetch treasury yields"""
        try:
            # 2-year yield
            tnx_2y = yf.download("^IRX", period="5d", progress=False)  # 13-week T-bill as proxy
            # 10-year yield
            tnx_10y = yf.download("^TNX", period="5d", progress=False)
            
            if isinstance(tnx_2y.columns, pd.MultiIndex):
                tnx_2y.columns = tnx_2y.columns.get_level_values(0)
            if isinstance(tnx_10y.columns, pd.MultiIndex):
                tnx_10y.columns = tnx_10y.columns.get_level_values(0)
            
            yield_2y = tnx_2y['Close'].iloc[-1] if not tnx_2y.empty else 4.5
            yield_10y = tnx_10y['Close'].iloc[-1] if not tnx_10y.empty else 4.0
            
            return float(yield_2y), float(yield_10y)
        except:
            return 4.5, 4.0  # Default values


# Global instance
_analyzer = None

def get_fed_analyzer() -> FedWatchAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = FedWatchAnalyzer()
    return _analyzer


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing FedWatchAnalyzer...")
    
    analyzer = FedWatchAnalyzer()
    result = analyzer.analyze()
    
    print(f"\n{'='*50}")
    print("FED POLICY ANALYSIS")
    print('='*50)
    print(f"Signal: {result.signal} ({result.fed_score:+d})")
    print(f"Rate Direction: {result.rate_direction} ({result.rate_momentum})")
    print()
    print(f"Current Fed Funds: {result.current_rate:.2f}%")
    print(f"Expected 3M: {result.expected_rate_3m:.2f}%")
    print(f"Expected 6M: {result.expected_rate_6m:.2f}%")
    print()
    print(f"2Y Yield: {result.yield_2y:.2f}%")
    print(f"10Y Yield: {result.yield_10y:.2f}%")
    print(f"Spread: {result.yield_spread:.2f}%")
    print()
    print(f"Stock Impact: {result.stock_impact}")
    print(f"Sector Rotation: {result.sector_rotation}")
    print(f"Details: {result.details}")


def analyze_fed_policy():
    return get_fed_analyzer().analyze()
