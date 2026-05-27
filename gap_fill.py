"""
Gap Fill Analysis
===================
Analyze and trade gap fills.
"""

from dataclasses import dataclass
from typing import Optional
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class GapAnalysis:
    symbol: str
    has_gap: bool
    gap_type: str  # "GAP_UP", "GAP_DOWN", "NONE"
    gap_size_pct: float
    gap_size_price: float
    
    prev_close: float
    open_price: float
    fill_target: float
    
    fill_probability: float
    
    tradeable: bool
    recommended_action: str
    entry: float
    stop: float
    target: float


class GapFillAnalyzer:
    """
    Gap Fill Trading Strategy
    
    Statistics:
    - 70%+ of gaps fill within 3 days
    - Small gaps (1-2%) fill most reliably
    - Large gaps (>5%) often don't fill quickly
    
    Strategy:
    - Gap up: Short or wait for fill
    - Gap down: Long toward fill
    """
    
    MIN_GAP_PCT = 0.5   # Minimum gap to trade
    MAX_GAP_PCT = 5.0   # Too large, don't trade
    
    def __init__(self):
        pass
    
    def analyze(self, symbol: str) -> GapAnalysis:
        """Analyze gap at market open"""
        
        try:
            # Get daily data
            df = yf.download(symbol, period='5d', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if df.empty or len(df) < 2:
                return self._no_gap(symbol)
            
            prev_close = float(df['Close'].iloc[-2])
            today_open = float(df['Open'].iloc[-1])
            today_high = float(df['High'].iloc[-1])
            today_low = float(df['Low'].iloc[-1])
            today_close = float(df['Close'].iloc[-1])
            
            # Calculate gap
            gap_pct = (today_open - prev_close) / prev_close * 100
            gap_size = today_open - prev_close
            
            # Determine gap type
            if gap_pct > self.MIN_GAP_PCT:
                gap_type = "GAP_UP"
            elif gap_pct < -self.MIN_GAP_PCT:
                gap_type = "GAP_DOWN"
            else:
                return self._no_gap(symbol)
            
            # Gap fill probability
            abs_gap = abs(gap_pct)
            if abs_gap < 1.5:
                fill_prob = 0.80
            elif abs_gap < 3.0:
                fill_prob = 0.65
            elif abs_gap < 5.0:
                fill_prob = 0.50
            else:
                fill_prob = 0.30
            
            # Check if already filled
            if gap_type == "GAP_UP" and today_low <= prev_close:
                return self._gap_filled(symbol, gap_type, gap_pct)
            elif gap_type == "GAP_DOWN" and today_high >= prev_close:
                return self._gap_filled(symbol, gap_type, gap_pct)
            
            # Tradeable?
            tradeable = self.MIN_GAP_PCT <= abs_gap <= self.MAX_GAP_PCT
            
            # Setup entry
            if gap_type == "GAP_UP":
                action = "SHORT toward gap fill"
                entry = today_close
                stop = today_high * 1.01
                target = prev_close
            else:
                action = "LONG toward gap fill"
                entry = today_close
                stop = today_low * 0.99
                target = prev_close
            
            return GapAnalysis(
                symbol=symbol,
                has_gap=True,
                gap_type=gap_type,
                gap_size_pct=gap_pct,
                gap_size_price=gap_size,
                prev_close=prev_close,
                open_price=today_open,
                fill_target=prev_close,
                fill_probability=fill_prob,
                tradeable=tradeable,
                recommended_action=action,
                entry=entry,
                stop=stop,
                target=target
            )
            
        except Exception as e:
            logger.debug(f"Gap analysis error: {e}")
            return self._no_gap(symbol)
    
    def _no_gap(self, symbol: str) -> GapAnalysis:
        return GapAnalysis(symbol, False, "NONE", 0, 0, 0, 0, 0, 0, False, "No gap", 0, 0, 0)
    
    def _gap_filled(self, symbol: str, gap_type: str, gap_pct: float) -> GapAnalysis:
        return GapAnalysis(symbol, True, gap_type, gap_pct, 0, 0, 0, 0, 1.0, 
                          False, "Gap already filled today", 0, 0, 0)


def get_gap_analyzer() -> GapFillAnalyzer:
    return GapFillAnalyzer()


if __name__ == "__main__":
    print("Testing GapFillAnalyzer...")
    ga = GapFillAnalyzer()
    
    for sym in ["AAPL", "NVDA", "TSLA"]:
        gap = ga.analyze(sym)
        print(f"\n{sym}:")
        print(f"  Gap: {gap.gap_type} ({gap.gap_size_pct:+.2f}%)")
        if gap.has_gap and gap.tradeable:
            print(f"  Fill Prob: {gap.fill_probability:.0%}")
            print(f"  Action: {gap.recommended_action}")
            print(f"  Entry: ${gap.entry:.2f}, Stop: ${gap.stop:.2f}, Target: ${gap.target:.2f}")
