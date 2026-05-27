"""
Oil Price Impact Analyzer
============================
Oil price impact on stocks and economy.
"""

from dataclasses import dataclass
from typing import List
import yfinance as yf
from loguru import logger


@dataclass
class OilImpact:
    oil_price: float
    oil_change_5d: float
    oil_change_30d: float
    
    # Trend
    trend: str  # "SPIKING", "RISING", "STABLE", "FALLING", "CRASHING"
    momentum: str  # "STRONG_UP", "UP", "NEUTRAL", "DOWN", "STRONG_DOWN"
    
    # Economic impact
    inflation_impact: str  # "INFLATIONARY", "NEUTRAL", "DEFLATIONARY"
    consumer_impact: str  # "NEGATIVE", "NEUTRAL", "POSITIVE"
    
    # Sector impact
    sector_winners: List[str]
    sector_losers: List[str]
    
    # Trading
    stock_impact: str
    recommendation: str

    @property
    def score(self) -> int:
        """
        Normalize Oil price trend into a stock trading score:
        - SPIKING (severe inflation/cost risk): -50
        - RISING (moderate cost drag): -20
        - CRASHING (demand collapse risk): -10
        - FALLING (consumer tailwind/lower input costs): +30
        - STABLE (goldilocks environment): +15
        """
        if self.trend == "SPIKING":
            return -50
        elif self.trend == "RISING":
            return -20
        elif self.trend == "CRASHING":
            return -10
        elif self.trend == "FALLING":
            return 30
        elif self.trend == "STABLE":
            return 15
        else:
            return 0



class OilImpactAnalyzer:
    """
    Oil Price Impact Analysis
    
    Why Oil Matters:
    1. Inflation driver
    2. Consumer spending power
    3. Energy sector profits
    4. Geopolitical barometer
    5. Economic demand indicator
    
    Scenarios:
    - Oil spike → Inflation → Fed hawkish → Stocks down
    - Oil crash → Demand concern → Recession fear
    - Stable oil → Goldilocks for stocks
    """
    
    # Sector impacts
    OIL_UP_WINNERS = ['XLE', 'OXY', 'XOM', 'CVX', 'SLB']  # Energy
    OIL_UP_LOSERS = ['JETS', 'UAL', 'DAL', 'XLY', 'HD']  # Airlines, Consumer
    
    OIL_DOWN_WINNERS = ['JETS', 'UAL', 'XLY', 'TGT', 'COST']  # Airlines, Consumer
    OIL_DOWN_LOSERS = ['XLE', 'OXY', 'XOM', 'CVX']  # Energy
    
    def __init__(self):
        pass
    
    def analyze(self) -> OilImpact:
        """Analyze oil price impact"""
        
        try:
            oil = yf.download('CL=F', period='3mo', progress=False)  # Crude futures
            if hasattr(oil.columns, 'get_level_values'):
                oil.columns = oil.columns.get_level_values(0)
            
            if oil.empty:
                # Try USO ETF
                oil = yf.download('USO', period='3mo', progress=False)
                if hasattr(oil.columns, 'get_level_values'):
                    oil.columns = oil.columns.get_level_values(0)
            
            if oil.empty:
                return self._default()
            
            current = float(oil['Close'].iloc[-1])
            d5 = float(oil['Close'].iloc[-5]) if len(oil) > 5 else current
            d30 = float(oil['Close'].iloc[-22]) if len(oil) > 22 else current
            
            change_5d = (current / d5 - 1) * 100
            change_30d = (current / d30 - 1) * 100
            
            # Trend
            if change_5d > 10:
                trend = "SPIKING"
                momentum = "STRONG_UP"
            elif change_5d > 3:
                trend = "RISING"
                momentum = "UP"
            elif change_5d < -10:
                trend = "CRASHING"
                momentum = "STRONG_DOWN"
            elif change_5d < -3:
                trend = "FALLING"
                momentum = "DOWN"
            else:
                trend = "STABLE"
                momentum = "NEUTRAL"
            
            # Economic impact
            if trend in ["SPIKING", "RISING"]:
                inflation = "INFLATIONARY"
                consumer = "NEGATIVE"
                winners = self.OIL_UP_WINNERS
                losers = self.OIL_UP_LOSERS
            elif trend in ["CRASHING", "FALLING"]:
                inflation = "DEFLATIONARY"
                consumer = "POSITIVE"
                winners = self.OIL_DOWN_WINNERS
                losers = self.OIL_DOWN_LOSERS
            else:
                inflation = "NEUTRAL"
                consumer = "NEUTRAL"
                winners = []
                losers = []
            
            # Stock impact
            if trend == "SPIKING":
                impact = "🚨 Oil spike → Inflation → Stocks pressured"
                rec = "Reduce consumer/airline, add energy. Watch Fed reaction."
            elif trend == "RISING":
                impact = "⚠️ Rising oil → Inflation pressure"
                rec = "Favor energy over consumer discretionary"
            elif trend == "CRASHING":
                impact = "⚠️ Oil crash → Demand concern or oversupply"
                rec = "Avoid energy, but watch for recession signals"
            elif trend == "FALLING":
                impact = "📊 Falling oil → Consumer tailwind"
                rec = "Favor airlines, consumer, travel"
            else:
                impact = "✅ Stable oil → Goldilocks for stocks"
                rec = "No oil-driven adjustment needed"
            
            return OilImpact(
                oil_price=current,
                oil_change_5d=change_5d,
                oil_change_30d=change_30d,
                trend=trend,
                momentum=momentum,
                inflation_impact=inflation,
                consumer_impact=consumer,
                sector_winners=winners[:3],
                sector_losers=losers[:3],
                stock_impact=impact,
                recommendation=rec
            )
            
        except Exception as e:
            logger.debug(f"Oil analysis error: {e}")
            return self._default()
    
    def _default(self) -> OilImpact:
        return OilImpact(
            70, 0, 0, "UNKNOWN", "NEUTRAL", "NEUTRAL", "NEUTRAL",
            [], [], "No data", "No oil data available"
        )


def get_oil_impact() -> OilImpactAnalyzer:
    return OilImpactAnalyzer()


if __name__ == "__main__":
    print("Testing OilImpactAnalyzer...")
    oi = OilImpactAnalyzer()
    
    sig = oi.analyze()
    
    print(f"\n{'='*50}")
    print("OIL PRICE IMPACT")
    print('='*50)
    print(f"Price: ${sig.oil_price:.2f}")
    print(f"5d: {sig.oil_change_5d:+.1f}%")
    print(f"30d: {sig.oil_change_30d:+.1f}%")
    print(f"\nTrend: {sig.trend}")
    print(f"Momentum: {sig.momentum}")
    print(f"\nInflation: {sig.inflation_impact}")
    print(f"Consumer: {sig.consumer_impact}")
    print(f"\nWinners: {sig.sector_winners}")
    print(f"Losers: {sig.sector_losers}")
    print(f"\nImpact: {sig.stock_impact}")
    print(f"Recommendation: {sig.recommendation}")
