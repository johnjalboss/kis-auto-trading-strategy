"""
Intermarket Analysis
======================
Analyze relationships between markets.
"""

from dataclasses import dataclass
from typing import Dict
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class IntermarketSignal:
    # Key markets
    dxy: float  # Dollar Index
    dxy_trend: str  # "UP", "DOWN", "FLAT"
    
    gold: float
    gold_trend: str
    
    oil: float
    oil_trend: str
    
    bonds_10y: float  # 10-year yield
    yield_trend: str
    
    vix: float
    vix_level: str  # "LOW", "NORMAL", "ELEVATED", "HIGH"
    
    # Analysis
    risk_sentiment: str  # "RISK_ON", "RISK_OFF", "MIXED"
    stock_outlook: str  # "BULLISH", "BEARISH", "NEUTRAL"
    
    key_insights: list
    trading_recommendation: str


class IntermarketAnalyzer:
    """
    Intermarket Analysis
    
    Key Relationships:
    
    1. Dollar (DXY) vs Stocks
       - Strong dollar = Headwind for multinationals
       - Weak dollar = Tailwind for stocks
    
    2. Yields vs Stocks
       - Rising yields = Growth stocks hurt
       - Falling yields = Growth stocks benefit
    
    3. Oil vs Economy
       - High oil = Inflation, hurts consumers
       - Low oil = Tailwind for economy
    
    4. Gold vs Risk
       - Rising gold = Flight to safety
       - Falling gold = Risk-on sentiment
    
    5. VIX vs Stocks
       - High VIX = Fear, potential bottom
       - Low VIX = Complacency, potential top
    """
    
    SYMBOLS = {
        'DXY': 'UUP',        # Dollar ETF (DX-Y.NYB not on KIS)
        'GOLD': 'GLD',
        'OIL': 'USO',
        'BONDS': 'TLT',
        'VIX': '^VIX',
        'SPY': 'SPY'
    }
    
    def __init__(self):
        pass
    
    def analyze(self) -> IntermarketSignal:
        """Run full intermarket analysis"""
        
        try:
            data = {}
            trends = {}
            
            for name, symbol in self.SYMBOLS.items():
                try:
                    df = yf.download(symbol, period='1mo', progress=False)
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    
                    if not df.empty:
                        current = float(df['Close'].iloc[-1])
                        sma10 = float(df['Close'].rolling(10).mean().iloc[-1])
                        change_5d = (current / float(df['Close'].iloc[-5]) - 1) * 100
                        
                        data[name] = current
                        
                        if change_5d > 1:
                            trends[name] = "UP"
                        elif change_5d < -1:
                            trends[name] = "DOWN"
                        else:
                            trends[name] = "FLAT"
                except:
                    data[name] = 0
                    trends[name] = "FLAT"
            
            # VIX level
            vix = data.get('VIX', 20)
            if vix > 30:
                vix_level = "HIGH"
            elif vix > 25:
                vix_level = "ELEVATED"
            elif vix > 18:
                vix_level = "NORMAL"
            else:
                vix_level = "LOW"
            
            # Risk sentiment
            insights = []
            
            # Dollar analysis
            if trends.get('DXY') == "UP":
                insights.append("Strong dollar - headwind for multinationals")
            elif trends.get('DXY') == "DOWN":
                insights.append("Weak dollar - tailwind for stocks")
            
            # Gold/VIX = fear gauge
            if trends.get('GOLD') == "UP" and vix > 20:
                risk = "RISK_OFF"
                insights.append("Gold up + VIX elevated = Risk-off environment")
            elif trends.get('GOLD') == "DOWN" and vix < 18:
                risk = "RISK_ON"
                insights.append("Gold down + low VIX = Risk-on environment")
            else:
                risk = "MIXED"
            
            # Bond/Yield analysis
            if trends.get('BONDS') == "DOWN":  # Bonds down = yields up
                insights.append("Rising yields - pressure on growth stocks")
            elif trends.get('BONDS') == "UP":
                insights.append("Falling yields - support for growth stocks")
            
            # Oil analysis
            if trends.get('OIL') == "UP":
                insights.append("Rising oil - inflation concern")
            elif trends.get('OIL') == "DOWN":
                insights.append("Falling oil - easing inflation pressure")
            
            # Stock outlook
            bullish_count = sum([
                trends.get('DXY') == "DOWN",
                trends.get('BONDS') == "UP",
                vix < 20,
                trends.get('SPY') == "UP"
            ])
            
            if bullish_count >= 3:
                outlook = "BULLISH"
                rec = "Conditions favor stocks - can be more aggressive"
            elif bullish_count <= 1:
                outlook = "BEARISH"
                rec = "Headwinds present - be defensive"
            else:
                outlook = "NEUTRAL"
                rec = "Mixed signals - selective trading"
            
            return IntermarketSignal(
                dxy=data.get('DXY', 100),
                dxy_trend=trends.get('DXY', 'FLAT'),
                gold=data.get('GOLD', 180),
                gold_trend=trends.get('GOLD', 'FLAT'),
                oil=data.get('OIL', 70),
                oil_trend=trends.get('OIL', 'FLAT'),
                bonds_10y=data.get('BONDS', 90),
                yield_trend=trends.get('BONDS', 'FLAT'),
                vix=vix,
                vix_level=vix_level,
                risk_sentiment=risk,
                stock_outlook=outlook,
                key_insights=insights,
                trading_recommendation=rec
            )
            
        except Exception as e:
            logger.error(f"Intermarket analysis error: {e}")
            return self._default()
    
    def _default(self) -> IntermarketSignal:
        return IntermarketSignal(
            100, "FLAT", 180, "FLAT", 70, "FLAT", 90, "FLAT", 20, "NORMAL",
            "MIXED", "NEUTRAL", [], "No data available"
        )


def get_intermarket() -> IntermarketAnalyzer:
    return IntermarketAnalyzer()


if __name__ == "__main__":
    print("Testing IntermarketAnalyzer...")
    im = IntermarketAnalyzer()
    
    sig = im.analyze()
    
    print(f"\n{'='*50}")
    print("INTERMARKET ANALYSIS")
    print('='*50)
    print(f"Dollar (DXY): {sig.dxy:.2f} ({sig.dxy_trend})")
    print(f"Gold: ${sig.gold:.2f} ({sig.gold_trend})")
    print(f"Oil: ${sig.oil:.2f} ({sig.oil_trend})")
    print(f"Bonds: ${sig.bonds_10y:.2f} ({sig.yield_trend})")
    print(f"VIX: {sig.vix:.1f} ({sig.vix_level})")
    print()
    print(f"Risk Sentiment: {sig.risk_sentiment}")
    print(f"Stock Outlook: {sig.stock_outlook}")
    print()
    print("Insights:")
    for i in sig.key_insights:
        print(f"  • {i}")
    print(f"\nRecommendation: {sig.trading_recommendation}")


def analyze_intermarket():
    return IntermarketSignal().get()
