"""
Market Psychology Analyzer
============================
Analyze crowd psychology and sentiment.
"""

from dataclasses import dataclass
from typing import List
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class PsychologyState:
    # Fear & Greed components
    vix_signal: str
    vix_level: float
    put_call_ratio: float
    put_call_signal: str
    
    # Market breadth
    advance_decline: str
    new_highs_lows: str
    
    # Momentum
    momentum_signal: str
    rsi_market: float
    
    # Overall
    fear_greed_score: int  # 0=Extreme Fear, 100=Extreme Greed
    state: str  # "EXTREME_FEAR", "FEAR", "NEUTRAL", "GREED", "EXTREME_GREED"
    
    # Trading implications
    contrarian_signal: str
    crowd_position: str
    recommendation: str


class MarketPsychology:
    """
    Market Psychology Analyzer
    
    Components (like CNN Fear & Greed):
    1. VIX (Fear Index)
    2. Put/Call Ratio
    3. Market Breadth
    4. Safe Haven Demand
    5. Momentum
    
    Contrarian Strategy:
    - Extreme Fear → Buy opportunity
    - Extreme Greed → Caution/Sell
    """
    
    def analyze(self) -> PsychologyState:
        """Run full psychology analysis"""
        
        score_components = []
        
        # 1. VIX Analysis
        vix_data = self._get_vix()
        vix_level = vix_data['level']
        
        if vix_level > 30:
            vix_signal = "EXTREME_FEAR"
            vix_score = 10
        elif vix_level > 25:
            vix_signal = "FEAR"
            vix_score = 25
        elif vix_level > 20:
            vix_signal = "ELEVATED"
            vix_score = 40
        elif vix_level > 15:
            vix_signal = "NEUTRAL"
            vix_score = 60
        else:
            vix_signal = "COMPLACENT"
            vix_score = 85
        
        score_components.append(vix_score)
        
        # 2. Put/Call Ratio (inverted - high = fear)
        pcr = self._get_put_call()
        
        if pcr > 1.2:
            pcr_signal = "EXTREME_FEAR"
            pcr_score = 15
        elif pcr > 1.0:
            pcr_signal = "FEAR"
            pcr_score = 30
        elif pcr > 0.8:
            pcr_signal = "NEUTRAL"
            pcr_score = 50
        elif pcr > 0.6:
            pcr_signal = "GREED"
            pcr_score = 70
        else:
            pcr_signal = "EXTREME_GREED"
            pcr_score = 90
        
        score_components.append(pcr_score)
        
        # 3. Market Momentum (S&P 500 RSI)
        spy_rsi = self._get_market_rsi()
        
        if spy_rsi > 70:
            mom_signal = "OVERBOUGHT"
            mom_score = 85
        elif spy_rsi > 60:
            mom_signal = "BULLISH"
            mom_score = 70
        elif spy_rsi > 40:
            mom_signal = "NEUTRAL"
            mom_score = 50
        elif spy_rsi > 30:
            mom_signal = "BEARISH"
            mom_score = 30
        else:
            mom_signal = "OVERSOLD"
            mom_score = 15
        
        score_components.append(mom_score)
        
        # 4. Breadth (using SPY internals as proxy)
        breadth = self._get_breadth()
        score_components.append(breadth['score'])
        
        # Calculate overall Fear & Greed Score
        fg_score = int(np.mean(score_components))
        
        # Determine state
        if fg_score <= 20:
            state = "EXTREME_FEAR"
        elif fg_score <= 40:
            state = "FEAR"
        elif fg_score <= 60:
            state = "NEUTRAL"
        elif fg_score <= 80:
            state = "GREED"
        else:
            state = "EXTREME_GREED"
        
        # Contrarian signal
        if fg_score <= 25:
            contrarian = "STRONG_BUY"
            crowd = "Panic selling"
            rec = "Accumulate quality stocks"
        elif fg_score <= 40:
            contrarian = "BUY"
            crowd = "Fearful"
            rec = "Selective buying"
        elif fg_score >= 80:
            contrarian = "STRONG_SELL"
            crowd = "Euphoric"
            rec = "Take profits, raise cash"
        elif fg_score >= 65:
            contrarian = "CAUTION"
            crowd = "Complacent"
            rec = "Tighten stops"
        else:
            contrarian = "NEUTRAL"
            crowd = "Balanced"
            rec = "Normal strategy"
        
        return PsychologyState(
            vix_signal=vix_signal,
            vix_level=vix_level,
            put_call_ratio=pcr,
            put_call_signal=pcr_signal,
            advance_decline=breadth['ad'],
            new_highs_lows=breadth['hl'],
            momentum_signal=mom_signal,
            rsi_market=spy_rsi,
            fear_greed_score=fg_score,
            state=state,
            contrarian_signal=contrarian,
            crowd_position=crowd,
            recommendation=rec
        )
    
    def _get_vix(self) -> dict:
        try:
            vix = yf.download("^VIX", period="5d", progress=False)
            if isinstance(vix.columns, pd.MultiIndex):
                vix.columns = vix.columns.get_level_values(0)
            level = float(vix['Close'].iloc[-1])
            return {'level': level}
        except:
            return {'level': 20}
    
    def _get_put_call(self) -> float:
        # Estimated from market conditions
        # In real implementation, get from CBOE
        return 0.85
    
    def _get_market_rsi(self) -> float:
        try:
            spy = yf.download("SPY", period="1mo", progress=False)
            if isinstance(spy.columns, pd.MultiIndex):
                spy.columns = spy.columns.get_level_values(0)
            close = spy['Close']
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss.replace(0, 1)
            rsi = 100 - (100 / (1 + rs))
            return float(rsi.iloc[-1])
        except:
            return 50
    
    def _get_breadth(self) -> dict:
        # Simplified - use SPY momentum as proxy
        try:
            spy = yf.download("SPY", period="1mo", progress=False)
            if isinstance(spy.columns, pd.MultiIndex):
                spy.columns = spy.columns.get_level_values(0)
            ret = (spy['Close'].iloc[-1] / spy['Close'].iloc[-5] - 1) * 100
            
            if ret > 2:
                return {'score': 75, 'ad': 'POSITIVE', 'hl': 'MORE_HIGHS'}
            elif ret > 0:
                return {'score': 60, 'ad': 'NEUTRAL', 'hl': 'BALANCED'}
            elif ret > -2:
                return {'score': 40, 'ad': 'NEUTRAL', 'hl': 'BALANCED'}
            else:
                return {'score': 25, 'ad': 'NEGATIVE', 'hl': 'MORE_LOWS'}
        except:
            return {'score': 50, 'ad': 'NEUTRAL', 'hl': 'BALANCED'}


def get_market_psychology() -> MarketPsychology:
    return MarketPsychology()


if __name__ == "__main__":
    print("Testing MarketPsychology...")
    mp = MarketPsychology()
    
    state = mp.analyze()
    
    print(f"\n{'='*50}")
    print("MARKET PSYCHOLOGY")
    print('='*50)
    print(f"Fear & Greed Score: {state.fear_greed_score}/100")
    print(f"State: {state.state}")
    print()
    print(f"VIX: {state.vix_level:.1f} ({state.vix_signal})")
    print(f"Put/Call: {state.put_call_ratio:.2f} ({state.put_call_signal})")
    print(f"RSI: {state.rsi_market:.1f} ({state.momentum_signal})")
    print()
    print(f"Crowd: {state.crowd_position}")
    print(f"Contrarian: {state.contrarian_signal}")
    print(f"Recommendation: {state.recommendation}")
