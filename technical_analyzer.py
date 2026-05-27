"""
Technical Analyzer
====================
Comprehensive technical analysis.
"""

from dataclasses import dataclass
from typing import List, Optional
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class TechnicalSignal:
    symbol: str
    
    # Trend
    trend: str  # "UPTREND", "DOWNTREND", "SIDEWAYS"
    trend_strength: int  # 0-100
    
    # Moving Averages
    above_sma20: bool
    above_sma50: bool
    above_sma200: bool
    golden_cross: bool
    death_cross: bool
    
    # Oscillators
    rsi: float
    rsi_signal: str  # "OVERBOUGHT", "OVERSOLD", "NEUTRAL"
    macd_signal: str  # "BULLISH", "BEARISH", "NEUTRAL"
    stoch_signal: str
    
    # Support/Resistance
    near_support: bool
    near_resistance: bool
    distance_to_support_pct: float
    distance_to_resistance_pct: float
    
    # Volume
    volume_trend: str  # "INCREASING", "DECREASING", "NORMAL"
    
    # Overall
    technical_score: int  # -100 to +100
    signal: str  # "STRONG_BUY", "BUY", "NEUTRAL", "SELL", "STRONG_SELL"
    details: List[str]


class TechnicalAnalyzer:
    """
    Technical Analysis Engine
    
    Indicators:
    1. Trend: SMA 20/50/200
    2. Momentum: RSI, MACD, Stochastic
    3. Support/Resistance
    4. Volume Analysis
    """
    
    def __init__(self):
        pass
    
    def analyze(self, symbol: str) -> TechnicalSignal:
        df = self._fetch_data(symbol)
        
        if df is None or len(df) < 200:
            return self._neutral(symbol)
        
        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume']
        
        details = []
        score = 0
        
        # Moving Averages
        sma20 = close.rolling(20).mean()
        sma50 = close.rolling(50).mean()
        sma200 = close.rolling(200).mean()
        
        current = float(close.iloc[-1])
        above_20 = current > sma20.iloc[-1]
        above_50 = current > sma50.iloc[-1]
        above_200 = current > sma200.iloc[-1]
        
        # Trend
        if above_20 and above_50 and above_200:
            trend = "UPTREND"
            trend_strength = 80
            score += 25
            details.append("STRONG_UPTREND")
        elif not above_20 and not above_50 and not above_200:
            trend = "DOWNTREND"
            trend_strength = 80
            score -= 25
            details.append("STRONG_DOWNTREND")
        else:
            trend = "SIDEWAYS"
            trend_strength = 40
        
        # Golden/Death Cross
        golden = sma50.iloc[-1] > sma200.iloc[-1] and sma50.iloc[-5] <= sma200.iloc[-5]
        death = sma50.iloc[-1] < sma200.iloc[-1] and sma50.iloc[-5] >= sma200.iloc[-5]
        
        if golden:
            score += 20
            details.append("GOLDEN_CROSS")
        if death:
            score -= 20
            details.append("DEATH_CROSS")
        
        # RSI
        rsi = self._calc_rsi(close)
        if rsi < 30:
            rsi_sig = "OVERSOLD"
            score += 15
            details.append(f"RSI_OVERSOLD:{rsi:.0f}")
        elif rsi > 70:
            rsi_sig = "OVERBOUGHT"
            score -= 15
            details.append(f"RSI_OVERBOUGHT:{rsi:.0f}")
        else:
            rsi_sig = "NEUTRAL"
        
        # MACD
        macd, signal_line = self._calc_macd(close)
        if macd > signal_line and macd > 0:
            macd_sig = "BULLISH"
            score += 15
        elif macd < signal_line and macd < 0:
            macd_sig = "BEARISH"
            score -= 15
        else:
            macd_sig = "NEUTRAL"
        
        # Stochastic
        stoch = self._calc_stoch(high, low, close)
        if stoch < 20:
            stoch_sig = "OVERSOLD"
            score += 10
        elif stoch > 80:
            stoch_sig = "OVERBOUGHT"
            score -= 10
        else:
            stoch_sig = "NEUTRAL"
        
        # Support/Resistance
        support = low.rolling(20).min().iloc[-1]
        resistance = high.rolling(20).max().iloc[-1]
        
        dist_support = (current - support) / current * 100
        dist_resist = (resistance - current) / current * 100
        
        near_support = dist_support < 2
        near_resist = dist_resist < 2
        
        if near_support:
            score += 10
            details.append("NEAR_SUPPORT")
        if near_resist:
            score -= 5
            details.append("NEAR_RESISTANCE")
        
        # Volume
        vol_avg = volume.rolling(20).mean().iloc[-1]
        vol_recent = volume.iloc[-5:].mean()
        
        if vol_recent > vol_avg * 1.5:
            vol_trend = "INCREASING"
        elif vol_recent < vol_avg * 0.7:
            vol_trend = "DECREASING"
        else:
            vol_trend = "NORMAL"
        
        # Final Signal
        if score >= 40:
            signal = "STRONG_BUY"
        elif score >= 15:
            signal = "BUY"
        elif score <= -40:
            signal = "STRONG_SELL"
        elif score <= -15:
            signal = "SELL"
        else:
            signal = "NEUTRAL"
        
        return TechnicalSignal(
            symbol=symbol,
            trend=trend,
            trend_strength=trend_strength,
            above_sma20=above_20,
            above_sma50=above_50,
            above_sma200=above_200,
            golden_cross=golden,
            death_cross=death,
            rsi=rsi,
            rsi_signal=rsi_sig,
            macd_signal=macd_sig,
            stoch_signal=stoch_sig,
            near_support=near_support,
            near_resistance=near_resist,
            distance_to_support_pct=dist_support,
            distance_to_resistance_pct=dist_resist,
            volume_trend=vol_trend,
            technical_score=score,
            signal=signal,
            details=details
        )
    
    def _calc_rsi(self, close: pd.Series, period: int = 14) -> float:
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss.replace(0, 1)
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])
    
    def _calc_macd(self, close: pd.Series):
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9).mean()
        return float(macd.iloc[-1]), float(signal.iloc[-1])
    
    def _calc_stoch(self, high, low, close, period: int = 14) -> float:
        lowest = low.rolling(period).min()
        highest = high.rolling(period).max()
        stoch = (close - lowest) / (highest - lowest) * 100
        return float(stoch.iloc[-1])
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        try:
            df = yf.download(symbol, period='1y', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return None
    
    def _neutral(self, symbol: str) -> TechnicalSignal:
        return TechnicalSignal(symbol, "UNKNOWN", 0, False, False, False, False, False,
                               50, "NEUTRAL", "NEUTRAL", "NEUTRAL", False, False, 0, 0,
                               "NORMAL", 0, "NEUTRAL", [])


def get_technical_analyzer() -> TechnicalAnalyzer:
    return TechnicalAnalyzer()


if __name__ == "__main__":
    print("Testing TechnicalAnalyzer...")
    ta = TechnicalAnalyzer()
    
    for sym in ["AAPL", "NVDA", "TSLA"]:
        t = ta.analyze(sym)
        print(f"\n{sym}:")
        print(f"  Trend: {t.trend} (strength: {t.trend_strength})")
        print(f"  SMAs: >20={t.above_sma20} >50={t.above_sma50} >200={t.above_sma200}")
        print(f"  RSI: {t.rsi:.1f} ({t.rsi_signal})")
        print(f"  MACD: {t.macd_signal}")
        print(f"  Score: {t.technical_score:+d} → {t.signal}")
        print(f"  Details: {t.details}")
