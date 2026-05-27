"""
Order Flow Analyzer
====================
Analyze buy/sell pressure and order flow imbalance.

Metrics:
1. Up Volume vs Down Volume
2. Money Flow Index (MFI)
3. Accumulation/Distribution
4. On-Balance Volume Divergence
5. Tick Imbalance (proxy)
"""

from dataclasses import dataclass
from typing import Optional, List, Dict
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class OrderFlowSignal:
    """Order flow analysis result"""
    symbol: str
    
    # Volume analysis
    up_volume_ratio: float  # 0-1 (1 = all buying)
    down_volume_ratio: float
    net_flow: float  # Positive = buying pressure
    
    # Indicators
    mfi: float  # 0-100
    ad_line_trend: str  # "UP", "DOWN", "NEUTRAL"
    obv_divergence: str  # "BULLISH", "BEARISH", "NONE"
    
    # Aggregate
    flow_score: int  # -100 to +100
    pressure: str  # "STRONG_BUY", "BUY", "NEUTRAL", "SELL", "STRONG_SELL"
    
    details: List[str]


class OrderFlowAnalyzer:
    """
    Order Flow Analysis
    
    Institutional Edge:
    - Volume at price = where institutions are active
    - Up/Down volume ratio = buying vs selling pressure
    - OBV divergence = smart money accumulation
    
    Scoring:
    - Up volume > 60%: +30 (buying dominant)
    - MFI < 30: +20 (oversold, reversal)
    - MFI > 70: -20 (overbought)
    - A/D rising: +20
    - OBV bullish divergence: +30
    """
    
    def __init__(self):
        self._cache: Dict[str, tuple] = {}
    
    def analyze(self, symbol: str) -> OrderFlowSignal:
        """Analyze order flow"""
        df = self._fetch_data(symbol)
        
        if df is None or len(df) < 30:
            return self._neutral_result(symbol)
        
        details = []
        score = 0
        
        # 1. Up/Down Volume Analysis
        up_vol, down_vol = self._calculate_volume_ratio(df)
        net_flow = up_vol - down_vol
        
        if up_vol > 0.6:
            score += 30
            details.append(f"BUYING_PRESSURE:{up_vol:.0%}")
        elif down_vol > 0.6:
            score -= 30
            details.append(f"SELLING_PRESSURE:{down_vol:.0%}")
        
        # 2. Money Flow Index
        mfi = self._calculate_mfi(df)
        
        if mfi < 30:
            score += 20
            details.append(f"MFI_OVERSOLD:{mfi:.0f}")
        elif mfi > 70:
            score -= 20
            details.append(f"MFI_OVERBOUGHT:{mfi:.0f}")
        
        # 3. Accumulation/Distribution
        ad_trend = self._calculate_ad_trend(df)
        
        if ad_trend == "UP":
            score += 20
            details.append("AD_ACCUMULATION")
        elif ad_trend == "DOWN":
            score -= 20
            details.append("AD_DISTRIBUTION")
        
        # 4. OBV Divergence
        obv_div = self._detect_obv_divergence(df)
        
        if obv_div == "BULLISH":
            score += 30
            details.append("OBV_BULLISH_DIVERGENCE")
        elif obv_div == "BEARISH":
            score -= 30
            details.append("OBV_BEARISH_DIVERGENCE")
        
        # 5. Volume Climax Detection
        vol_climax = self._detect_volume_climax(df)
        if vol_climax == "EXHAUSTION_TOP":
            score -= 25
            details.append("VOLUME_CLIMAX_TOP")
        elif vol_climax == "EXHAUSTION_BOTTOM":
            score += 25
            details.append("VOLUME_CLIMAX_BOTTOM")
        
        # Determine pressure
        if score >= 50:
            pressure = "STRONG_BUY"
        elif score >= 20:
            pressure = "BUY"
        elif score <= -50:
            pressure = "STRONG_SELL"
        elif score <= -20:
            pressure = "SELL"
        else:
            pressure = "NEUTRAL"
        
        return OrderFlowSignal(
            symbol=symbol,
            up_volume_ratio=up_vol,
            down_volume_ratio=down_vol,
            net_flow=net_flow,
            mfi=mfi,
            ad_line_trend=ad_trend,
            obv_divergence=obv_div,
            flow_score=max(-100, min(100, score)),
            pressure=pressure,
            details=details
        )
    
    def _calculate_volume_ratio(self, df: pd.DataFrame) -> tuple:
        """Calculate up/down volume ratio"""
        close = df['Close']
        volume = df['Volume']
        
        # Volume on up days vs down days
        price_change = close.diff()
        
        up_vol = volume[price_change > 0].tail(10).sum()
        down_vol = volume[price_change < 0].tail(10).sum()
        total_vol = up_vol + down_vol
        
        if total_vol > 0:
            return up_vol / total_vol, down_vol / total_vol
        return 0.5, 0.5
    
    def _calculate_mfi(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Money Flow Index"""
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        raw_money_flow = typical_price * df['Volume']
        
        tp_diff = typical_price.diff()
        
        positive_flow = raw_money_flow.where(tp_diff > 0, 0).rolling(period).sum()
        negative_flow = raw_money_flow.where(tp_diff < 0, 0).rolling(period).sum()
        
        money_ratio = positive_flow / negative_flow.replace(0, 1)
        mfi = 100 - (100 / (1 + money_ratio))
        
        return mfi.iloc[-1] if not pd.isna(mfi.iloc[-1]) else 50
    
    def _calculate_ad_trend(self, df: pd.DataFrame) -> str:
        """Calculate Accumulation/Distribution trend"""
        high = df['High']
        low = df['Low']
        close = df['Close']
        volume = df['Volume']
        
        # CLV = ((Close - Low) - (High - Close)) / (High - Low)
        clv = ((close - low) - (high - close)) / (high - low).replace(0, 1)
        ad = (clv * volume).cumsum()
        
        # Trend of last 10 bars
        ad_sma = ad.rolling(5).mean()
        
        if ad_sma.iloc[-1] > ad_sma.iloc[-5]:
            return "UP"
        elif ad_sma.iloc[-1] < ad_sma.iloc[-5]:
            return "DOWN"
        return "NEUTRAL"
    
    def _detect_obv_divergence(self, df: pd.DataFrame) -> str:
        """Detect OBV divergence"""
        close = df['Close']
        volume = df['Volume']
        
        # Calculate OBV
        obv = (np.sign(close.diff()) * volume).cumsum()
        
        # Look for divergence in last 10 bars
        price_trend = close.iloc[-1] - close.iloc[-10]
        obv_trend = obv.iloc[-1] - obv.iloc[-10]
        
        # Bullish divergence: Price down, OBV up
        if price_trend < 0 and obv_trend > 0:
            return "BULLISH"
        # Bearish divergence: Price up, OBV down
        elif price_trend > 0 and obv_trend < 0:
            return "BEARISH"
        
        return "NONE"
    
    def _detect_volume_climax(self, df: pd.DataFrame) -> str:
        """Detect volume climax (exhaustion)"""
        close = df['Close']
        volume = df['Volume']
        
        vol_avg = volume.tail(20).mean()
        vol_std = volume.tail(20).std()
        
        # Volume spike (>2 std above mean)
        recent_vol = volume.iloc[-1]
        
        if recent_vol > vol_avg + 2 * vol_std:
            # High volume + price near high = potential top
            high_20 = close.tail(20).max()
            if close.iloc[-1] > high_20 * 0.98:
                return "EXHAUSTION_TOP"
            
            # High volume + price near low = potential bottom
            low_20 = close.tail(20).min()
            if close.iloc[-1] < low_20 * 1.02:
                return "EXHAUSTION_BOTTOM"
        
        return "NONE"
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch data"""
        try:
            df = yf.download(symbol, period='60d', interval='1d', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return None
    
    def _neutral_result(self, symbol: str) -> OrderFlowSignal:
        """Return neutral result"""
        return OrderFlowSignal(
            symbol=symbol, up_volume_ratio=0.5, down_volume_ratio=0.5,
            net_flow=0, mfi=50, ad_line_trend="NEUTRAL", obv_divergence="NONE",
            flow_score=0, pressure="NEUTRAL", details=[]
        )


# Global instance
_analyzer = None

def get_order_flow_analyzer() -> OrderFlowAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = OrderFlowAnalyzer()
    return _analyzer


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing OrderFlowAnalyzer...")
    
    analyzer = OrderFlowAnalyzer()
    
    for symbol in ["AAPL", "TSLA", "NVDA"]:
        print(f"\n{'='*50}")
        print(f"{symbol}")
        print('='*50)
        
        result = analyzer.analyze(symbol)
        
        print(f"Pressure: {result.pressure} ({result.flow_score:+d})")
        print(f"Up/Down Volume: {result.up_volume_ratio:.0%}/{result.down_volume_ratio:.0%}")
        print(f"MFI: {result.mfi:.0f}")
        print(f"A/D Trend: {result.ad_line_trend}")
        print(f"OBV Divergence: {result.obv_divergence}")
        print(f"Details: {result.details}")
