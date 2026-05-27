"""
Candlestick Pattern Detector
==============================
Detect Japanese candlestick patterns for reversal/continuation signals.

Patterns:
1. Reversal: Doji, Hammer, Engulfing, Morning/Evening Star
2. Continuation: Three Soldiers, Three Crows
3. Indecision: Spinning Top, Inside Bar
"""

from dataclasses import dataclass
from typing import Optional, List, Dict
import pandas as pd
import numpy as np
import kis_data as yf  # KIS API drop-in replacement
from loguru import logger


@dataclass
class CandlePattern:
    """Candlestick pattern"""
    name: str
    pattern_type: str   # "REVERSAL", "CONTINUATION", "INDECISION"
    direction: str      # "BULLISH", "BEARISH", "NEUTRAL"
    strength: int       # 1-3
    bar_index: int      # How many bars ago


@dataclass
class CandlestickSignal:
    """Candlestick analysis result"""
    symbol: str
    
    # Last candle
    last_open: float
    last_high: float
    last_low: float
    last_close: float
    last_body_pct: float  # Body size as % of range
    
    # Detected patterns
    patterns: List[CandlePattern]
    
    # Summary
    bullish_patterns: int
    bearish_patterns: int
    strongest_pattern: str
    
    # Scoring
    candle_score: int  # -100 to +100
    signal: str
    details: List[str]


class CandlestickDetector:
    """
    Japanese Candlestick Pattern Detection
    
    Bullish Reversal Patterns:
    - Hammer (long lower shadow)
    - Bullish Engulfing
    - Morning Star (3-bar)
    - Piercing Line
    
    Bearish Reversal Patterns:
    - Shooting Star (long upper shadow)
    - Bearish Engulfing
    - Evening Star (3-bar)
    - Dark Cloud Cover
    
    Continuation:
    - Three White Soldiers (bullish)
    - Three Black Crows (bearish)
    
    Scoring:
    - Strong reversal pattern: ±35
    - Moderate pattern: ±20
    - Weak/Indecision: ±5
    """
    
    def __init__(self):
        pass
    
    def analyze(self, symbol: str) -> CandlestickSignal:
        """Analyze candlestick patterns"""
        details = []
        score = 0
        patterns = []
        
        df = self._fetch_data(symbol)
        
        if df is None or len(df) < 10:
            return self._neutral_result(symbol)
        
        # Get OHLC
        opens = df['Open']
        highs = df['High']
        lows = df['Low']
        closes = df['Close']
        
        # Last candle stats
        last_o = opens.iloc[-1]
        last_h = highs.iloc[-1]
        last_l = lows.iloc[-1]
        last_c = closes.iloc[-1]
        
        candle_range = last_h - last_l
        body_size = abs(last_c - last_o)
        body_pct = (body_size / candle_range * 100) if candle_range > 0 else 50
        
        # Detect patterns
        
        # 1. Doji
        doji = self._detect_doji(opens, highs, lows, closes)
        if doji:
            patterns.append(doji)
            details.append("DOJI")
        
        # 2. Hammer / Shooting Star
        hammer = self._detect_hammer(opens, highs, lows, closes)
        if hammer:
            patterns.append(hammer)
            if hammer.direction == "BULLISH":
                score += 25
                details.append("HAMMER")
            else:
                score -= 25
                details.append("SHOOTING_STAR")
        
        # 3. Engulfing
        engulf = self._detect_engulfing(opens, highs, lows, closes)
        if engulf:
            patterns.append(engulf)
            if engulf.direction == "BULLISH":
                score += 35
                details.append("BULLISH_ENGULFING")
            else:
                score -= 35
                details.append("BEARISH_ENGULFING")
        
        # 4. Morning / Evening Star
        star = self._detect_star(opens, highs, lows, closes)
        if star:
            patterns.append(star)
            if star.direction == "BULLISH":
                score += 35
                details.append("MORNING_STAR")
            else:
                score -= 35
                details.append("EVENING_STAR")
        
        # 5. Three Soldiers / Crows
        soldiers = self._detect_three_soldiers(opens, closes)
        if soldiers:
            patterns.append(soldiers)
            if soldiers.direction == "BULLISH":
                score += 30
                details.append("THREE_WHITE_SOLDIERS")
            else:
                score -= 30
                details.append("THREE_BLACK_CROWS")
        
        # 6. Piercing / Dark Cloud
        piercing = self._detect_piercing(opens, highs, lows, closes)
        if piercing:
            patterns.append(piercing)
            if piercing.direction == "BULLISH":
                score += 20
                details.append("PIERCING_LINE")
            else:
                score -= 20
                details.append("DARK_CLOUD")
        
        # Count patterns
        bullish = len([p for p in patterns if p.direction == "BULLISH"])
        bearish = len([p for p in patterns if p.direction == "BEARISH"])
        
        # Strongest pattern
        if patterns:
            strongest = max(patterns, key=lambda x: x.strength)
            strongest_name = f"{strongest.name} ({strongest.direction})"
        else:
            strongest_name = "NONE"
        
        # Signal
        if score >= 30:
            signal = "CANDLE_BULLISH"
        elif score >= 15:
            signal = "CANDLE_SLIGHTLY_BULLISH"
        elif score <= -30:
            signal = "CANDLE_BEARISH"
        elif score <= -15:
            signal = "CANDLE_SLIGHTLY_BEARISH"
        else:
            signal = "CANDLE_NEUTRAL"
        
        return CandlestickSignal(
            symbol=symbol,
            last_open=last_o,
            last_high=last_h,
            last_low=last_l,
            last_close=last_c,
            last_body_pct=body_pct,
            patterns=patterns,
            bullish_patterns=bullish,
            bearish_patterns=bearish,
            strongest_pattern=strongest_name,
            candle_score=max(-100, min(100, score)),
            signal=signal,
            details=details
        )
    
    def _detect_doji(self, opens, highs, lows, closes) -> Optional[CandlePattern]:
        """Detect Doji (tiny body)"""
        o, h, l, c = opens.iloc[-1], highs.iloc[-1], lows.iloc[-1], closes.iloc[-1]
        
        body = abs(c - o)
        candle_range = h - l
        
        if candle_range > 0 and body / candle_range < 0.1:
            return CandlePattern(
                name="Doji",
                pattern_type="INDECISION",
                direction="NEUTRAL",
                strength=1,
                bar_index=0
            )
        return None
    
    def _detect_hammer(self, opens, highs, lows, closes) -> Optional[CandlePattern]:
        """Detect Hammer (bullish) or Shooting Star (bearish)"""
        o, h, l, c = opens.iloc[-1], highs.iloc[-1], lows.iloc[-1], closes.iloc[-1]
        
        body = abs(c - o)
        candle_range = h - l
        
        if candle_range == 0:
            return None
        
        lower_shadow = min(o, c) - l
        upper_shadow = h - max(o, c)
        
        # Hammer: Long lower shadow, small upper shadow
        if lower_shadow > body * 2 and upper_shadow < body * 0.5:
            return CandlePattern(
                name="Hammer",
                pattern_type="REVERSAL",
                direction="BULLISH",
                strength=2,
                bar_index=0
            )
        
        # Shooting Star: Long upper shadow, small lower shadow
        if upper_shadow > body * 2 and lower_shadow < body * 0.5:
            return CandlePattern(
                name="Shooting Star",
                pattern_type="REVERSAL",
                direction="BEARISH",
                strength=2,
                bar_index=0
            )
        
        return None
    
    def _detect_engulfing(self, opens, highs, lows, closes) -> Optional[CandlePattern]:
        """Detect Engulfing pattern"""
        if len(opens) < 2:
            return None
        
        o1, c1 = opens.iloc[-2], closes.iloc[-2]
        o2, c2 = opens.iloc[-1], closes.iloc[-1]
        
        body1 = abs(c1 - o1)
        body2 = abs(c2 - o2)
        
        # Bullish Engulfing
        if c1 < o1 and c2 > o2:  # Previous bearish, current bullish
            if c2 > o1 and o2 < c1:  # Current body engulfs previous
                return CandlePattern(
                    name="Bullish Engulfing",
                    pattern_type="REVERSAL",
                    direction="BULLISH",
                    strength=3,
                    bar_index=0
                )
        
        # Bearish Engulfing
        if c1 > o1 and c2 < o2:  # Previous bullish, current bearish
            if c2 < o1 and o2 > c1:  # Current body engulfs previous
                return CandlePattern(
                    name="Bearish Engulfing",
                    pattern_type="REVERSAL",
                    direction="BEARISH",
                    strength=3,
                    bar_index=0
                )
        
        return None
    
    def _detect_star(self, opens, highs, lows, closes) -> Optional[CandlePattern]:
        """Detect Morning Star (bullish) or Evening Star (bearish)"""
        if len(opens) < 3:
            return None
        
        o1, c1 = opens.iloc[-3], closes.iloc[-3]
        o2, c2 = opens.iloc[-2], closes.iloc[-2]
        o3, c3 = opens.iloc[-1], closes.iloc[-1]
        
        body1 = abs(c1 - o1)
        body2 = abs(c2 - o2)
        body3 = abs(c3 - o3)
        
        # Morning Star
        if c1 < o1 and body2 < body1 * 0.3 and c3 > o3 and c3 > (o1 + c1) / 2:
            return CandlePattern(
                name="Morning Star",
                pattern_type="REVERSAL",
                direction="BULLISH",
                strength=3,
                bar_index=0
            )
        
        # Evening Star
        if c1 > o1 and body2 < body1 * 0.3 and c3 < o3 and c3 < (o1 + c1) / 2:
            return CandlePattern(
                name="Evening Star",
                pattern_type="REVERSAL",
                direction="BEARISH",
                strength=3,
                bar_index=0
            )
        
        return None
    
    def _detect_three_soldiers(self, opens, closes) -> Optional[CandlePattern]:
        """Detect Three White Soldiers or Three Black Crows"""
        if len(opens) < 3:
            return None
        
        c1, c2, c3 = closes.iloc[-3], closes.iloc[-2], closes.iloc[-1]
        o1, o2, o3 = opens.iloc[-3], opens.iloc[-2], opens.iloc[-1]
        
        # Three White Soldiers
        if (c1 > o1 and c2 > o2 and c3 > o3 and
            c2 > c1 and c3 > c2):
            return CandlePattern(
                name="Three White Soldiers",
                pattern_type="CONTINUATION",
                direction="BULLISH",
                strength=3,
                bar_index=0
            )
        
        # Three Black Crows
        if (c1 < o1 and c2 < o2 and c3 < o3 and
            c2 < c1 and c3 < c2):
            return CandlePattern(
                name="Three Black Crows",
                pattern_type="CONTINUATION",
                direction="BEARISH",
                strength=3,
                bar_index=0
            )
        
        return None
    
    def _detect_piercing(self, opens, highs, lows, closes) -> Optional[CandlePattern]:
        """Detect Piercing Line or Dark Cloud Cover"""
        if len(opens) < 2:
            return None
        
        o1, h1, l1, c1 = opens.iloc[-2], highs.iloc[-2], lows.iloc[-2], closes.iloc[-2]
        o2, h2, l2, c2 = opens.iloc[-1], highs.iloc[-1], lows.iloc[-1], closes.iloc[-1]
        
        # Piercing Line
        if c1 < o1 and o2 < c1 and c2 > (o1 + c1) / 2 and c2 < o1:
            return CandlePattern(
                name="Piercing Line",
                pattern_type="REVERSAL",
                direction="BULLISH",
                strength=2,
                bar_index=0
            )
        
        # Dark Cloud Cover
        if c1 > o1 and o2 > c1 and c2 < (o1 + c1) / 2 and c2 > o1:
            return CandlePattern(
                name="Dark Cloud Cover",
                pattern_type="REVERSAL",
                direction="BEARISH",
                strength=2,
                bar_index=0
            )
        
        return None
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch data"""
        try:
            df = yf.download(symbol, period='30d', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return None
    
    def _neutral_result(self, symbol: str) -> CandlestickSignal:
        """Return neutral"""
        return CandlestickSignal(
            symbol=symbol, last_open=0, last_high=0, last_low=0, last_close=0,
            last_body_pct=50, patterns=[], bullish_patterns=0, bearish_patterns=0,
            strongest_pattern="NONE", candle_score=0, signal="NO_DATA", details=[]
        )


# Global
_detector = None

def get_candlestick_detector() -> CandlestickDetector:
    global _detector
    if _detector is None:
        _detector = CandlestickDetector()
    return _detector


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing CandlestickDetector...")
    
    detector = CandlestickDetector()
    
    for symbol in ["AAPL", "TSLA", "NVDA"]:
        print(f"\n{'='*50}")
        print(f"{symbol}")
        print('='*50)
        
        result = detector.analyze(symbol)
        
        print(f"Signal: {result.signal} ({result.candle_score:+d})")
        print(f"Last Candle: O:{result.last_open:.2f} H:{result.last_high:.2f} L:{result.last_low:.2f} C:{result.last_close:.2f}")
        print(f"Body %: {result.last_body_pct:.0f}%")
        print()
        print(f"Patterns Found: {len(result.patterns)}")
        for p in result.patterns:
            print(f"  {p.name} ({p.direction}, str={p.strength})")
        print(f"Strongest: {result.strongest_pattern}")
        print(f"Details: {result.details}")
