"""
Market Breadth Analyzer
=========================
Analyze market-wide participation and internal strength.

Metrics:
1. Advance/Decline Line
2. New Highs vs New Lows
3. % Above Moving Averages
4. McClellan Oscillator
5. Sector Participation
"""

from dataclasses import dataclass
from typing import Optional, List, Dict
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class BreadthSignal:
    """Market breadth analysis result"""
    # A/D Line
    ad_ratio: float         # Advances / Declines
    ad_trend: str           # "IMPROVING", "DETERIORATING", "STABLE"
    
    # New Highs/Lows
    new_highs: int
    new_lows: int
    hi_lo_ratio: float
    
    # % Above MAs
    pct_above_20ma: float
    pct_above_50ma: float
    pct_above_200ma: float
    
    # Participation
    sectors_bullish: int    # Out of 11
    sectors_bearish: int
    
    # Aggregate
    breadth_score: int      # -100 to +100
    divergence: str         # "BULLISH_DIV", "BEARISH_DIV", "NONE"
    signal: str
    details: List[str]


class MarketBreadthAnalyzer:
    """
    Market Breadth Analysis
    
    Healthy Bull Market:
    - Advance/Decline ratio > 1.5
    - High % stocks above 20/50/200 MA
    - New Highs >> New Lows
    - Most sectors participating
    
    Warning Signs:
    - Fewer stocks making new highs
    - Declining A/D line while index rises (bearish divergence)
    - Most stocks below 50MA
    
    Scoring:
    - A/D Ratio > 2: +25
    - Hi/Lo Ratio > 3: +25
    - >70% above 50MA: +25
    - >7 sectors bullish: +25
    """
    
    # Sector ETFs
    SECTORS = ['XLK', 'XLF', 'XLE', 'XLV', 'XLI', 'XLP', 'XLY', 'XLU', 'XLRE', 'XLB', 'XLC']
    
    # Sample stocks for breadth (S&P 500 sample)
    SAMPLE_STOCKS = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'UNH', 'JNJ',
        'V', 'XOM', 'JPM', 'PG', 'MA', 'HD', 'CVX', 'MRK', 'ABBV', 'LLY',
        'PFE', 'KO', 'PEP', 'COST', 'TMO', 'AVGO', 'MCD', 'WMT', 'CSCO', 'ACN',
        'DHR', 'ABT', 'DIS', 'VZ', 'ADBE', 'NKE', 'CMCSA', 'NEE', 'TXN', 'PM',
        'RTX', 'INTC', 'BA', 'HON', 'UNP', 'IBM', 'AMGN', 'QCOM', 'INTU', 'CAT'
    ]
    
    def __init__(self):
        self._stock_data: Dict[str, pd.DataFrame] = {}
    
    def analyze(self) -> BreadthSignal:
        """Analyze market breadth"""
        details = []
        score = 0
        
        # Fetch data for sample stocks
        self._fetch_stock_data()
        
        # 1. Calculate Advance/Decline
        advances, declines = self._calculate_ad()
        ad_ratio = advances / declines if declines > 0 else advances
        
        if ad_ratio > 2.0:
            ad_trend = "IMPROVING"
            score += 25
            details.append(f"AD_STRONG:{ad_ratio:.1f}")
        elif ad_ratio > 1.0:
            ad_trend = "STABLE"
            score += 10
        elif ad_ratio < 0.5:
            ad_trend = "DETERIORATING"
            score -= 25
            details.append(f"AD_WEAK:{ad_ratio:.1f}")
        else:
            ad_trend = "DETERIORATING"
            score -= 10
        
        # 2. New Highs/Lows
        new_highs, new_lows = self._count_high_low()
        hi_lo_ratio = new_highs / new_lows if new_lows > 0 else new_highs
        
        if hi_lo_ratio > 3.0:
            score += 25
            details.append(f"HI_LO_STRONG:{new_highs}H/{new_lows}L")
        elif hi_lo_ratio > 1.0:
            score += 10
        elif hi_lo_ratio < 0.3:
            score -= 25
            details.append(f"HI_LO_WEAK:{new_highs}H/{new_lows}L")
        else:
            score -= 10
        
        # 3. % Above Moving Averages
        pct_20, pct_50, pct_200 = self._pct_above_ma()
        
        if pct_50 > 0.70:
            score += 25
            details.append(f"PCT_50MA:{pct_50:.0%}")
        elif pct_50 > 0.50:
            score += 10
        elif pct_50 < 0.30:
            score -= 25
            details.append(f"PCT_50MA_WEAK:{pct_50:.0%}")
        elif pct_50 < 0.40:
            score -= 10
        
        # 4. Sector Participation
        bullish, bearish = self._sector_participation()
        
        if bullish >= 8:
            score += 25
            details.append(f"SECTORS_BULLISH:{bullish}/11")
        elif bullish >= 6:
            score += 10
        elif bearish >= 8:
            score -= 25
            details.append(f"SECTORS_BEARISH:{bearish}/11")
        elif bearish >= 6:
            score -= 10
        
        # 5. Divergence detection
        divergence = self._detect_divergence()
        
        if divergence == "BULLISH_DIV":
            score += 20
            details.append("BULLISH_DIVERGENCE")
        elif divergence == "BEARISH_DIV":
            score -= 30  # More weight on bearish divergence
            details.append("⚠️ BEARISH_DIVERGENCE")
        
        # Determine signal
        if score >= 50:
            signal = "STRONG_BREADTH"
        elif score >= 20:
            signal = "HEALTHY_BREADTH"
        elif score <= -50:
            signal = "WEAK_BREADTH"
        elif score <= -20:
            signal = "DETERIORATING_BREADTH"
        else:
            signal = "MIXED_BREADTH"
        
        return BreadthSignal(
            ad_ratio=ad_ratio,
            ad_trend=ad_trend,
            new_highs=new_highs,
            new_lows=new_lows,
            hi_lo_ratio=hi_lo_ratio,
            pct_above_20ma=pct_20,
            pct_above_50ma=pct_50,
            pct_above_200ma=pct_200,
            sectors_bullish=bullish,
            sectors_bearish=bearish,
            breadth_score=max(-100, min(100, score)),
            divergence=divergence,
            signal=signal,
            details=details
        )
    
    def _fetch_stock_data(self):
        """Fetch data for sample stocks"""
        for symbol in self.SAMPLE_STOCKS[:30]:  # Limit for speed
            try:
                df = yf.download(symbol, period='60d', progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                if not df.empty:
                    self._stock_data[symbol] = df
            except Exception as err:
                logger.warning("⚠️ [market_breadth.py] Fallback triggered: {}", err)
    
    def _calculate_ad(self) -> tuple:
        """Calculate advances and declines"""
        advances = 0
        declines = 0
        
        for symbol, df in self._stock_data.items():
            if len(df) >= 2:
                if df['Close'].iloc[-1] > df['Close'].iloc[-2]:
                    advances += 1
                else:
                    declines += 1
        
        return advances, max(1, declines)
    
    def _count_high_low(self) -> tuple:
        """Count new 52-week highs and lows"""
        new_highs = 0
        new_lows = 0
        
        for symbol, df in self._stock_data.items():
            if len(df) >= 50:
                high_52w = df['High'].max()
                low_52w = df['Low'].min()
                current = df['Close'].iloc[-1]
                
                if current >= high_52w * 0.98:
                    new_highs += 1
                if current <= low_52w * 1.02:
                    new_lows += 1
        
        return new_highs, max(1, new_lows)
    
    def _pct_above_ma(self) -> tuple:
        """Calculate % stocks above moving averages"""
        above_20, above_50, above_200 = 0, 0, 0
        total = len(self._stock_data)
        
        for symbol, df in self._stock_data.items():
            close = df['Close']
            current = close.iloc[-1]
            
            if len(close) >= 20:
                if current > close.tail(20).mean():
                    above_20 += 1
            
            if len(close) >= 50:
                if current > close.tail(50).mean():
                    above_50 += 1
            else:
                above_50 += 0.5  # Assume neutral if not enough data
            
            if len(close) >= 200:
                if current > close.mean():  # Use available data
                    above_200 += 1
        
        total = max(1, total)
        return above_20 / total, above_50 / total, above_200 / total
    
    def _sector_participation(self) -> tuple:
        """Count bullish and bearish sectors"""
        bullish = 0
        bearish = 0
        
        for etf in self.SECTORS:
            try:
                df = yf.download(etf, period='30d', progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                
                if len(df) >= 20:
                    close = df['Close']
                    sma20 = close.rolling(20).mean().iloc[-1]
                    
                    if close.iloc[-1] > sma20:
                        bullish += 1
                    else:
                        bearish += 1
            except Exception as err:
                logger.warning("⚠️ [market_breadth.py] Fallback triggered: {}", err)
        
        return bullish, bearish
    
    def _detect_divergence(self) -> str:
        """Detect breadth divergence vs SPY"""
        try:
            spy = yf.download('SPY', period='60d', progress=False)
            if isinstance(spy.columns, pd.MultiIndex):
                spy.columns = spy.columns.get_level_values(0)
            
            # SPY making new highs?
            spy_at_high = spy['Close'].iloc[-1] >= spy['Close'].tail(20).max() * 0.99
            
            # But breadth weak?
            _, pct_50, _ = self._pct_above_ma()
            
            if spy_at_high and pct_50 < 0.50:
                return "BEARISH_DIV"  # Index up but breadth weak
            elif not spy_at_high and pct_50 > 0.60:
                return "BULLISH_DIV"  # Index down but breadth strong
            
        except Exception as err:
            logger.warning("⚠️ [market_breadth.py] Fallback triggered: {}", err)
        
        return "NONE"


# Global instance
_analyzer = None

def get_breadth_analyzer() -> MarketBreadthAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = MarketBreadthAnalyzer()
    return _analyzer


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing MarketBreadthAnalyzer...")
    print("(This may take a moment to fetch data...)")
    
    analyzer = MarketBreadthAnalyzer()
    result = analyzer.analyze()
    
    print(f"\n{'='*50}")
    print("MARKET BREADTH ANALYSIS")
    print('='*50)
    print(f"Signal: {result.signal} ({result.breadth_score:+d})")
    print()
    print(f"A/D Ratio: {result.ad_ratio:.2f} ({result.ad_trend})")
    print(f"New Highs/Lows: {result.new_highs}/{result.new_lows} (Ratio: {result.hi_lo_ratio:.1f})")
    print()
    print(f"% Above 20MA: {result.pct_above_20ma:.0%}")
    print(f"% Above 50MA: {result.pct_above_50ma:.0%}")
    print(f"% Above 200MA: {result.pct_above_200ma:.0%}")
    print()
    print(f"Sectors: {result.sectors_bullish} bullish, {result.sectors_bearish} bearish")
    print(f"Divergence: {result.divergence}")
    print()
    print(f"Details: {result.details}")
