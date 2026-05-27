"""
Seasonality Analyzer
======================
Monthly and weekly trading patterns.
"""

from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime
import pandas as pd
import yfinance as yf
from loguru import logger


@dataclass
class SeasonalEdge:
    period: str
    avg_return: float
    win_rate: float
    is_bullish: bool
    strength: str  # "STRONG", "MODERATE", "WEAK"


@dataclass
class SeasonalAnalysis:
    symbol: str
    current_month: str
    current_day: str
    
    monthly_edge: SeasonalEdge
    weekly_edge: SeasonalEdge
    
    combined_bias: str  # "BULLISH", "BEARISH", "NEUTRAL"
    trading_recommendation: str


class SeasonalityAnalyzer:
    """
    Seasonality Trading Edges
    
    Known Patterns:
    - January Effect (small caps)
    - Sell in May
    - October Turnaround
    - Santa Claus Rally
    - Monday Effect
    - Month-end Window Dressing
    """
    
    # Historical monthly tendencies (S&P 500)
    MONTHLY_BIAS = {
        1: ('January', 1.5, 60, "BULLISH"),
        2: ('February', -0.2, 48, "NEUTRAL"),
        3: ('March', 1.2, 58, "BULLISH"),
        4: ('April', 1.5, 62, "BULLISH"),
        5: ('May', 0.2, 52, "NEUTRAL"),
        6: ('June', -0.1, 48, "NEUTRAL"),
        7: ('July', 1.0, 56, "BULLISH"),
        8: ('August', 0.0, 50, "NEUTRAL"),
        9: ('September', -0.8, 45, "BEARISH"),
        10: ('October', 0.8, 55, "NEUTRAL"),
        11: ('November', 1.5, 62, "BULLISH"),
        12: ('December', 1.3, 60, "BULLISH"),
    }
    
    # Weekly patterns
    WEEKLY_BIAS = {
        0: ('Monday', -0.1, 48, "BEARISH"),
        1: ('Tuesday', 0.1, 52, "NEUTRAL"),
        2: ('Wednesday', 0.15, 53, "NEUTRAL"),
        3: ('Thursday', 0.12, 52, "NEUTRAL"),
        4: ('Friday', 0.05, 51, "NEUTRAL"),
        5: ('Saturday', 0.0, 50, "NEUTRAL"),  # Weekend
        6: ('Sunday', 0.0, 50, "NEUTRAL"),    # Weekend
    }
    
    def __init__(self):
        pass
    
    def analyze(self, symbol: str = "SPY") -> SeasonalAnalysis:
        """Get seasonal analysis"""
        
        now = datetime.now()
        month = now.month
        weekday = now.weekday()
        
        # Get monthly edge
        month_name, m_ret, m_wr, m_bias = self.MONTHLY_BIAS[month]
        monthly = SeasonalEdge(
            period=month_name,
            avg_return=m_ret,
            win_rate=m_wr,
            is_bullish=m_bias == "BULLISH",
            strength="STRONG" if abs(m_ret) > 1.0 else "MODERATE" if abs(m_ret) > 0.5 else "WEAK"
        )
        
        # Get weekly edge
        day_name, d_ret, d_wr, d_bias = self.WEEKLY_BIAS[weekday]
        weekly = SeasonalEdge(
            period=day_name,
            avg_return=d_ret,
            win_rate=d_wr,
            is_bullish=d_bias == "BULLISH",
            strength="MODERATE" if abs(d_ret) > 0.1 else "WEAK"
        )
        
        # Special periods
        special = self._check_special_periods(now)
        
        # Combined bias
        if monthly.is_bullish and d_bias != "BEARISH":
            combined = "BULLISH"
            rec = f"Seasonal tailwind: {month_name} historically +{m_ret:.1f}%"
        elif m_bias == "BEARISH" or d_bias == "BEARISH":
            combined = "BEARISH"
            rec = "Seasonal headwind - reduce exposure"
        else:
            combined = "NEUTRAL"
            rec = "No strong seasonal bias"
        
        if special:
            rec += f" | {special}"
        
        return SeasonalAnalysis(
            symbol=symbol,
            current_month=month_name,
            current_day=day_name,
            monthly_edge=monthly,
            weekly_edge=weekly,
            combined_bias=combined,
            trading_recommendation=rec
        )
    
    def _check_special_periods(self, now: datetime) -> str:
        """Check for special seasonal periods"""
        
        month = now.month
        day = now.day
        
        # Santa Claus Rally (Dec 24 - Jan 2)
        if (month == 12 and day >= 24) or (month == 1 and day <= 2):
            return "🎅 Santa Claus Rally period"
        
        # Month-end (last 3 days)
        if day >= 28:
            return "📊 Month-end window dressing"
        
        # Triple Witching (3rd Friday of Mar, Jun, Sep, Dec)
        if month in [3, 6, 9, 12]:
            if now.weekday() == 4 and 15 <= day <= 21:
                return "⚠️ Triple Witching - high volatility"
        
        # First week of month (fund flows)
        if day <= 5:
            return "💰 Month-start fund inflows"
        
        return ""
    
    def get_best_months(self) -> List[str]:
        """Get historically best months"""
        return ['November', 'April', 'January', 'December']
    
    def get_worst_months(self) -> List[str]:
        """Get historically worst months"""
        return ['September', 'June', 'August']


def get_seasonality() -> SeasonalityAnalyzer:
    return SeasonalityAnalyzer()


if __name__ == "__main__":
    print("Testing SeasonalityAnalyzer...")
    sa = SeasonalityAnalyzer()
    
    analysis = sa.analyze()
    
    print(f"\n{'='*50}")
    print(f"SEASONALITY ANALYSIS")
    print('='*50)
    print(f"Date: {analysis.current_month} / {analysis.current_day}")
    print(f"\nMonthly: {analysis.monthly_edge.period}")
    print(f"  Avg Return: {analysis.monthly_edge.avg_return:+.1f}%")
    print(f"  Win Rate: {analysis.monthly_edge.win_rate}%")
    print(f"  Strength: {analysis.monthly_edge.strength}")
    print(f"\nWeekly: {analysis.weekly_edge.period}")
    print(f"  Avg Return: {analysis.weekly_edge.avg_return:+.2f}%")
    print(f"\nCombined: {analysis.combined_bias}")
    print(f"Recommendation: {analysis.trading_recommendation}")
