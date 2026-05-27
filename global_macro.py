"""
Global Macro Analyzer
========================
World events impact on US stocks.
"""

from dataclasses import dataclass
from typing import List, Dict
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class GlobalMacroSignal:
    # Risk Sentiment
    overall_risk: str  # "RISK_ON", "RISK_OFF", "CAUTION"
    risk_score: int  # 0-100 (higher = more risk-off)
    
    # Component Signals
    usd_strength: str  # Strong dollar = headwind
    oil_signal: str
    crypto_signal: str
    yen_carry_risk: str
    china_signal: str
    europe_signal: str
    
    # Alerts
    active_alerts: List[str]
    
    # Trading
    stock_bias: str
    position_size_mult: float
    sectors_to_avoid: List[str]
    sectors_to_favor: List[str]
    
    recommendation: str

    @property
    def score(self) -> int:
        """
        Normalize Macro risk_score into a directional trading score.
        - RISK_OFF (-80)
        - CAUTION (-40)
        - RISK_ON (+40)
        - NEUTRAL (0)
        """
        if self.overall_risk == "RISK_OFF":
            return -80
        elif self.overall_risk == "CAUTION":
            return -40
        elif self.overall_risk == "RISK_ON":
            return 40
        else:
            return 0



class GlobalMacroAnalyzer:
    """
    Global Macro Analysis
    
    Key Factors:
    1. USD Strength (DXY)
    2. Oil Price (affects inflation)
    3. Bitcoin (risk sentiment)
    4. Yen Carry Trade (JPY strength = risk-off)
    5. China (FXI, KWEB)
    6. Europe (EZU, VGK)
    7. Emerging Markets (EEM)
    
    Risk-Off Triggers:
    - Yen strengthening rapidly
    - VIX spiking
    - Bitcoin crashing
    - Oil spiking (inflation fear)
    """
    
    SYMBOLS = {
        # Major indices
        'SPY': 'SPY',        # S&P 500
        'QQQ': 'QQQ',        # Nasdaq
        
        # Currency
        'DXY': 'UUP',        # Dollar ETF (DX-Y.NYB often fails)
        'USDJPY': 'FXY',     # Yen ETF (inverse)
        
        # Commodities
        'OIL': 'USO',
        'GOLD': 'GLD',
        
        # Crypto
        'BTC': 'BTC-USD',
        
        # Global
        'CHINA': 'FXI',
        'EUROPE': 'VGK',
        'EMERGING': 'EEM',
        
        # Risk
        'VIX': '^VIX',
    }
    
    def __init__(self):
        self.data_cache = {}
    
    def analyze(self) -> GlobalMacroSignal:
        """Run full global macro analysis"""
        
        # Fetch all data
        self._fetch_data()
        
        alerts = []
        risk_score = 50  # Neutral
        
        # 1. USD Analysis
        usd = self._analyze_usd()
        if usd['signal'] == "STRONG":
            risk_score += 10
            alerts.append("💵 Strong USD - headwind for multinationals")
        
        # 2. Oil Analysis
        oil = self._analyze_oil()
        if oil['signal'] == "SPIKING":
            risk_score += 15
            alerts.append("🛢️ Oil spiking - inflation concern")
        elif oil['signal'] == "CRASHING":
            risk_score += 5
            alerts.append("🛢️ Oil crashing - demand concern")
        
        # 3. Crypto (Risk Sentiment)
        crypto = self._analyze_crypto()
        if crypto['signal'] == "CRASHING":
            risk_score += 20
            alerts.append("₿ Crypto crashing - risk-off sentiment")
        elif crypto['signal'] == "RALLYING":
            risk_score -= 10
        
        # 4. Yen Carry Trade
        yen = self._analyze_yen_carry()
        if yen['signal'] == "UNWINDING":
            risk_score += 25
            alerts.append("🇯🇵 YEN CARRY UNWINDING - Major risk-off!")
        
        # 5. China
        china = self._analyze_china()
        if china['signal'] == "WEAK":
            risk_score += 10
            alerts.append("🇨🇳 China weakness - global demand risk")
        
        # 6. Europe
        europe = self._analyze_europe()
        if europe['signal'] == "WEAK":
            risk_score += 5
            alerts.append("🇪🇺 Europe weakness")
        
        # Determine overall risk
        if risk_score >= 80:
            overall = "RISK_OFF"
            bias = "BEARISH"
            size_mult = 0.3
        elif risk_score >= 60:
            overall = "CAUTION"
            bias = "NEUTRAL"
            size_mult = 0.6
        elif risk_score <= 30:
            overall = "RISK_ON"
            bias = "BULLISH"
            size_mult = 1.2
        else:
            overall = "NEUTRAL"
            bias = "NEUTRAL"
            size_mult = 1.0
        
        # Sector recommendations
        avoid = []
        favor = []
        
        if oil['signal'] == "SPIKING":
            avoid.extend(['XLY', 'JETS'])  # Consumer, Airlines
            favor.append('XLE')  # Energy
        
        if usd['signal'] == "STRONG":
            avoid.extend(['EEM', 'XLB'])  # EM, Materials
            favor.append('XLU')  # Utilities
        
        if yen['signal'] == "UNWINDING":
            avoid.extend(['XLF', 'XLK'])  # Financials, Tech
            favor.extend(['XLU', 'GLD'])  # Utilities, Gold
        
        # Recommendation
        if overall == "RISK_OFF":
            rec = "🚨 RISK-OFF: Reduce exposure, hedge with gold/bonds"
        elif overall == "CAUTION":
            rec = "⚠️ CAUTION: Reduce position sizes, avoid aggressive entries"
        elif overall == "RISK_ON":
            rec = "✅ RISK-ON: Favorable conditions for stocks"
        else:
            rec = "Neutral global macro environment"
        
        return GlobalMacroSignal(
            overall_risk=overall,
            risk_score=risk_score,
            usd_strength=usd['signal'],
            oil_signal=oil['signal'],
            crypto_signal=crypto['signal'],
            yen_carry_risk=yen['signal'],
            china_signal=china['signal'],
            europe_signal=europe['signal'],
            active_alerts=alerts,
            stock_bias=bias,
            position_size_mult=size_mult,
            sectors_to_avoid=avoid,
            sectors_to_favor=favor,
            recommendation=rec
        )
    
    def _fetch_data(self):
        """Fetch all market data"""
        for name, symbol in self.SYMBOLS.items():
            try:
                df = yf.download(symbol, period='1mo', progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                if not df.empty:
                    self.data_cache[name] = df
            except:
                pass
    
    def _get_change(self, name: str, days: int = 5) -> float:
        """Get % change over n days"""
        df = self.data_cache.get(name)
        if df is None or len(df) < days:
            return 0
        return (float(df['Close'].iloc[-1]) / float(df['Close'].iloc[-days]) - 1) * 100
    
    def _analyze_usd(self) -> Dict:
        chg = self._get_change('DXY')
        if chg > 2:
            return {'signal': 'STRONG', 'change': chg}
        elif chg < -2:
            return {'signal': 'WEAK', 'change': chg}
        return {'signal': 'NEUTRAL', 'change': chg}
    
    def _analyze_oil(self) -> Dict:
        chg = self._get_change('OIL')
        if chg > 10:
            return {'signal': 'SPIKING', 'change': chg}
        elif chg < -10:
            return {'signal': 'CRASHING', 'change': chg}
        return {'signal': 'STABLE', 'change': chg}
    
    def _analyze_crypto(self) -> Dict:
        chg = self._get_change('BTC')
        if chg < -15:
            return {'signal': 'CRASHING', 'change': chg}
        elif chg > 15:
            return {'signal': 'RALLYING', 'change': chg}
        return {'signal': 'STABLE', 'change': chg}
    
    def _analyze_yen_carry(self) -> Dict:
        """Yen carry unwind = JPY strengthening = FXY rising"""
        chg = self._get_change('USDJPY')  # FXY is inverse of USD/JPY
        if chg > 3:  # Yen strengthening
            return {'signal': 'UNWINDING', 'change': chg}
        elif chg < -2:
            return {'signal': 'BUILDING', 'change': chg}
        return {'signal': 'STABLE', 'change': chg}
    
    def _analyze_china(self) -> Dict:
        chg = self._get_change('CHINA')
        if chg < -5:
            return {'signal': 'WEAK', 'change': chg}
        elif chg > 5:
            return {'signal': 'STRONG', 'change': chg}
        return {'signal': 'NEUTRAL', 'change': chg}
    
    def _analyze_europe(self) -> Dict:
        chg = self._get_change('EUROPE')
        if chg < -3:
            return {'signal': 'WEAK', 'change': chg}
        elif chg > 3:
            return {'signal': 'STRONG', 'change': chg}
        return {'signal': 'NEUTRAL', 'change': chg}


def get_global_macro() -> GlobalMacroAnalyzer:
    return GlobalMacroAnalyzer()


if __name__ == "__main__":
    print("Testing GlobalMacroAnalyzer...")
    gm = GlobalMacroAnalyzer()
    
    sig = gm.analyze()
    
    print(f"\n{'='*60}")
    print("GLOBAL MACRO ANALYSIS")
    print('='*60)
    print(f"Overall: {sig.overall_risk} (Score: {sig.risk_score}/100)")
    print(f"\nComponents:")
    print(f"  USD: {sig.usd_strength}")
    print(f"  Oil: {sig.oil_signal}")
    print(f"  Crypto: {sig.crypto_signal}")
    print(f"  Yen Carry: {sig.yen_carry_risk}")
    print(f"  China: {sig.china_signal}")
    print(f"  Europe: {sig.europe_signal}")
    print(f"\nAlerts:")
    for a in sig.active_alerts:
        print(f"  {a}")
    print(f"\nStock Bias: {sig.stock_bias}")
    print(f"Position Size: {sig.position_size_mult:.1f}x")
    print(f"Avoid: {sig.sectors_to_avoid}")
    print(f"Favor: {sig.sectors_to_favor}")
    print(f"\nRecommendation: {sig.recommendation}")
