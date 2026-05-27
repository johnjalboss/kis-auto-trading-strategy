"""
Divergence Detector
======================
Detect bullish and bearish divergences between price and indicators.

Divergence Types:
1. Regular Bullish - Price lower low, indicator higher low
2. Regular Bearish - Price higher high, indicator lower high
3. Hidden Bullish - Price higher low, indicator lower low
4. Hidden Bearish - Price lower high, indicator higher high
"""

from dataclasses import dataclass
from typing import Optional, List, Dict
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class Divergence:
    """Divergence data"""
    divergence_type: str  # "REGULAR_BULLISH", "REGULAR_BEARISH", "HIDDEN_BULLISH", "HIDDEN_BEARISH"
    indicator: str        # "RSI", "MACD", "OBV"
    strength: int         # 1-3
    price_point1: float
    price_point2: float
    indicator_point1: float
    indicator_point2: float


@dataclass
class DivergenceSignal:
    """Divergence analysis result"""
    symbol: str
    
    # Detected divergences
    divergences: List[Divergence]
    
    # Summary
    has_bullish: bool
    has_bearish: bool
    strongest_divergence: str
    
    # Current indicator values
    rsi: float
    macd: float
    macd_signal: float
    macd_histogram: float
    
    # Scoring
    divergence_score: int  # -100 to +100
    signal: str
    details: List[str]


class DivergenceDetector:
    """
    Price-Indicator Divergence Detection
    
    Regular Divergences (Reversal signals):
    - Bullish: Price makes lower low, RSI makes higher low
    - Bearish: Price makes higher high, RSI makes lower high
    
    Hidden Divergences (Continuation signals):
    - Bullish: Price makes higher low, RSI makes lower low
    - Bearish: Price makes lower high, RSI makes higher high
    
    Scoring:
    - Regular bullish divergence: +40
    - Regular bearish divergence: -40
    - Hidden bullish: +25
    - Hidden bearish: -25
    - Multiple divergences: ±15 bonus
    """
    
    def __init__(self, lookback: int = 60):
        self.lookback = lookback
    
    def analyze(self, symbol: str) -> DivergenceSignal:
        """Analyze for divergences"""
        details = []
        score = 0
        divergences = []
        
        df = self._fetch_data(symbol)
        
        if df is None or len(df) < 30:
            return self._neutral_result(symbol)
        
        close = df['Close']
        
        # Calculate indicators
        rsi = self._calculate_rsi(close)
        macd, macd_signal, macd_hist = self._calculate_macd(close)
        obv = self._calculate_obv(df)
        
        current_rsi = rsi.iloc[-1]
        current_macd = macd.iloc[-1]
        current_macd_signal = macd_signal.iloc[-1]
        current_macd_hist = macd_hist.iloc[-1]
        
        # Detect divergences for RSI
        rsi_divs = self._detect_divergences(close, rsi, "RSI")
        divergences.extend(rsi_divs)
        
        # Detect divergences for MACD histogram
        macd_divs = self._detect_divergences(close, macd_hist, "MACD")
        divergences.extend(macd_divs)
        
        # Detect divergences for OBV
        obv_divs = self._detect_divergences(close, obv, "OBV")
        divergences.extend(obv_divs)
        
        # Score divergences
        has_bullish = False
        has_bearish = False
        
        for div in divergences:
            if "BULLISH" in div.divergence_type:
                has_bullish = True
                if "REGULAR" in div.divergence_type:
                    score += 40
                    details.append(f"REG_BULL_DIV:{div.indicator}")
                else:
                    score += 25
                    details.append(f"HID_BULL_DIV:{div.indicator}")
            else:
                has_bearish = True
                if "REGULAR" in div.divergence_type:
                    score -= 40
                    details.append(f"REG_BEAR_DIV:{div.indicator}")
                else:
                    score -= 25
                    details.append(f"HID_BEAR_DIV:{div.indicator}")
        
        # Multiple divergence bonus
        bullish_count = len([d for d in divergences if "BULLISH" in d.divergence_type])
        bearish_count = len([d for d in divergences if "BEARISH" in d.divergence_type])
        
        if bullish_count >= 2:
            score += 15
            details.append("MULTI_BULL_DIV")
        if bearish_count >= 2:
            score -= 15
            details.append("MULTI_BEAR_DIV")
        
        # Strongest divergence
        if divergences:
            regular_divs = [d for d in divergences if "REGULAR" in d.divergence_type]
            if regular_divs:
                strongest = regular_divs[0].divergence_type
            else:
                strongest = divergences[0].divergence_type
        else:
            strongest = "NONE"
        
        # Signal
        if score >= 40:
            signal = "STRONG_BULLISH_DIVERGENCE"
        elif score >= 20:
            signal = "BULLISH_DIVERGENCE"
        elif score <= -40:
            signal = "STRONG_BEARISH_DIVERGENCE"
        elif score <= -20:
            signal = "BEARISH_DIVERGENCE"
        else:
            signal = "NO_DIVERGENCE"
        
        return DivergenceSignal(
            symbol=symbol,
            divergences=divergences,
            has_bullish=has_bullish,
            has_bearish=has_bearish,
            strongest_divergence=strongest,
            rsi=current_rsi,
            macd=current_macd,
            macd_signal=current_macd_signal,
            macd_histogram=current_macd_hist,
            divergence_score=max(-100, min(100, score)),
            signal=signal,
            details=details
        )
    
    def _detect_divergences(self, price: pd.Series, indicator: pd.Series, 
                            ind_name: str) -> List[Divergence]:
        """Detect divergences between price and indicator"""
        divergences = []
        
        # Find swing lows and highs in last 20 bars
        price_recent = price.tail(20)
        ind_recent = indicator.tail(20)
        
        if len(price_recent) < 10:
            return divergences
        
        # Find swing lows (for bullish divergence)
        price_lows = self._find_swing_lows(price_recent)
        ind_lows = self._find_swing_lows(ind_recent)
        
        # Find swing highs (for bearish divergence)
        price_highs = self._find_swing_highs(price_recent)
        ind_highs = self._find_swing_highs(ind_recent)
        
        # Check for regular bullish divergence
        # Price: lower low, Indicator: higher low
        if len(price_lows) >= 2 and len(ind_lows) >= 2:
            p1, p2 = price_lows[-2], price_lows[-1]
            i1, i2 = ind_lows[-2], ind_lows[-1]
            
            if p2 < p1 and i2 > i1:
                divergences.append(Divergence(
                    divergence_type="REGULAR_BULLISH",
                    indicator=ind_name,
                    strength=3,
                    price_point1=p1, price_point2=p2,
                    indicator_point1=i1, indicator_point2=i2
                ))
            # Hidden bullish: Price higher low, indicator lower low
            elif p2 > p1 and i2 < i1:
                divergences.append(Divergence(
                    divergence_type="HIDDEN_BULLISH",
                    indicator=ind_name,
                    strength=2,
                    price_point1=p1, price_point2=p2,
                    indicator_point1=i1, indicator_point2=i2
                ))
        
        # Check for regular bearish divergence
        # Price: higher high, Indicator: lower high
        if len(price_highs) >= 2 and len(ind_highs) >= 2:
            p1, p2 = price_highs[-2], price_highs[-1]
            i1, i2 = ind_highs[-2], ind_highs[-1]
            
            if p2 > p1 and i2 < i1:
                divergences.append(Divergence(
                    divergence_type="REGULAR_BEARISH",
                    indicator=ind_name,
                    strength=3,
                    price_point1=p1, price_point2=p2,
                    indicator_point1=i1, indicator_point2=i2
                ))
            # Hidden bearish: Price lower high, indicator higher high
            elif p2 < p1 and i2 > i1:
                divergences.append(Divergence(
                    divergence_type="HIDDEN_BEARISH",
                    indicator=ind_name,
                    strength=2,
                    price_point1=p1, price_point2=p2,
                    indicator_point1=i1, indicator_point2=i2
                ))
        
        return divergences
    
    def _find_swing_lows(self, series: pd.Series) -> List[float]:
        """Find swing lows"""
        lows = []
        values = series.values
        
        for i in range(2, len(values) - 2):
            if (values[i] < values[i-1] and values[i] < values[i-2] and
                values[i] < values[i+1] and values[i] < values[i+2]):
                lows.append(values[i])
        
        return lows[-3:] if lows else []
    
    def _find_swing_highs(self, series: pd.Series) -> List[float]:
        """Find swing highs"""
        highs = []
        values = series.values
        
        for i in range(2, len(values) - 2):
            if (values[i] > values[i-1] and values[i] > values[i-2] and
                values[i] > values[i+1] and values[i] > values[i+2]):
                highs.append(values[i])
        
        return highs[-3:] if highs else []
    
    def _calculate_rsi(self, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss.replace(0, 1)
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, close: pd.Series) -> tuple:
        """Calculate MACD"""
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9).mean()
        histogram = macd - signal
        return macd, signal, histogram
    
    def _calculate_obv(self, df: pd.DataFrame) -> pd.Series:
        """Calculate OBV"""
        close = df['Close']
        volume = df['Volume']
        
        direction = np.where(close.diff() > 0, 1, -1)
        direction[0] = 0
        
        return (volume * direction).cumsum()
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch data"""
        try:
            df = yf.download(symbol, period=f'{self.lookback}d', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return None
    
    def _neutral_result(self, symbol: str) -> DivergenceSignal:
        """Return neutral"""
        return DivergenceSignal(
            symbol=symbol, divergences=[], has_bullish=False, has_bearish=False,
            strongest_divergence="NONE", rsi=50, macd=0, macd_signal=0, macd_histogram=0,
            divergence_score=0, signal="NO_DATA", details=[]
        )


# Global
_detector = None

def get_divergence_detector() -> DivergenceDetector:
    global _detector
    if _detector is None:
        _detector = DivergenceDetector()
    return _detector


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing DivergenceDetector...")
    
    detector = DivergenceDetector()
    
    for symbol in ["AAPL", "TSLA", "NVDA"]:
        print(f"\n{'='*50}")
        print(f"{symbol}")
        print('='*50)
        
        result = detector.analyze(symbol)
        
        print(f"Signal: {result.signal} ({result.divergence_score:+d})")
        print(f"Has Bullish: {result.has_bullish}")
        print(f"Has Bearish: {result.has_bearish}")
        print(f"Strongest: {result.strongest_divergence}")
        print()
        print(f"RSI: {result.rsi:.1f}")
        print(f"MACD: {result.macd:.3f} (Hist: {result.macd_histogram:.3f})")
        print()
        print(f"Divergences: {len(result.divergences)}")
        for d in result.divergences:
            print(f"  {d.divergence_type} ({d.indicator})")
        print(f"Details: {result.details}")
