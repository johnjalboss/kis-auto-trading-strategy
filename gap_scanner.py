"""
Gap Scanner
=============
Pre-market gap analysis for momentum trading.

Gap Types:
1. Gap Up: Open > Previous Close (bullish)
2. Gap Down: Open < Previous Close (bearish)
3. Gap Fill: Price returns to fill gap (reversal)

Filters:
- Gap size (minimum 2%)
- Volume confirmation
- Technical levels (support/resistance)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class GapStock:
    """Stock with gap"""
    symbol: str
    gap_pct: float
    gap_type: str  # "GAP_UP", "GAP_DOWN"
    prev_close: float
    open_price: float
    current_price: float
    
    volume_ratio: float  # vs average
    atr_ratio: float  # gap size vs ATR
    
    above_vwap: bool
    gap_filled: bool
    
    score: int  # 0-100
    signal: str  # "LONG", "SHORT", "FADE", "AVOID"


@dataclass
class GapScanResult:
    """Gap scan results"""
    scan_time: datetime
    
    gap_ups: List[GapStock]
    gap_downs: List[GapStock]
    
    best_long_candidates: List[GapStock]
    best_short_candidates: List[GapStock]
    fade_candidates: List[GapStock]
    
    market_bias: str  # "BULLISH", "BEARISH", "NEUTRAL"


class GapScanner:
    """
    Pre-market Gap Scanner
    
    Strategies:
    1. Gap & Go: Trade in gap direction with momentum
       - High volume, strong relative strength
       - Gap holds above VWAP
    
    2. Gap Fill/Fade: Trade reversal
       - Overextended gap (>3x ATR)
       - Weak volume, gap starting to fill
    
    Scoring:
    - Gap size: 2-5% optimal (20 pts)
    - Volume: >2x average (20 pts)
    - ATR: 1-3x ATR (20 pts)
    - Technical: Above VWAP/key levels (20 pts)
    - Catalyst: News/earnings (20 pts)
    """
    
    MIN_GAP_PCT = 0.02  # 2% minimum gap
    MAX_GAP_PCT = 0.15  # 15% maximum (avoid halts)
    
    def __init__(self):
        self._cache: Dict[str, pd.DataFrame] = {}
    
    def scan(self, symbols: List[str]) -> GapScanResult:
        """Scan for gaps in given symbols"""
        gap_ups = []
        gap_downs = []
        
        for symbol in symbols:
            try:
                gap = self._analyze_gap(symbol)
                if gap:
                    if gap.gap_type == "GAP_UP":
                        gap_ups.append(gap)
                    else:
                        gap_downs.append(gap)
            except Exception as e:
                logger.debug("Gap scan failed for {}: {}", symbol, e)
        
        # Sort by score
        gap_ups.sort(key=lambda x: x.score, reverse=True)
        gap_downs.sort(key=lambda x: x.score, reverse=True)
        
        # Categorize candidates
        best_longs = [g for g in gap_ups if g.signal == "LONG"][:5]
        best_shorts = [g for g in gap_downs if g.signal == "SHORT"][:5]
        fades = [g for g in (gap_ups + gap_downs) if g.signal == "FADE"][:3]
        
        # Determine market bias
        total_gap_up_volume = sum(g.volume_ratio for g in gap_ups)
        total_gap_down_volume = sum(g.volume_ratio for g in gap_downs)
        
        if len(gap_ups) > len(gap_downs) * 1.5 and total_gap_up_volume > total_gap_down_volume:
            market_bias = "BULLISH"
        elif len(gap_downs) > len(gap_ups) * 1.5 and total_gap_down_volume > total_gap_up_volume:
            market_bias = "BEARISH"
        else:
            market_bias = "NEUTRAL"
        
        return GapScanResult(
            scan_time=datetime.now(),
            gap_ups=gap_ups,
            gap_downs=gap_downs,
            best_long_candidates=best_longs,
            best_short_candidates=best_shorts,
            fade_candidates=fades,
            market_bias=market_bias
        )
    
    def _analyze_gap(self, symbol: str) -> Optional[GapStock]:
        """Analyze gap for a single stock"""
        df = self._fetch_data(symbol)
        if df is None or len(df) < 20:
            return None
        
        # Get prices
        prev_close = df['Close'].iloc[-2]
        open_price = df['Open'].iloc[-1]
        current_price = df['Close'].iloc[-1]
        
        gap_pct = (open_price - prev_close) / prev_close
        
        # Check minimum gap
        if abs(gap_pct) < self.MIN_GAP_PCT:
            return None
        
        # Check maximum gap
        if abs(gap_pct) > self.MAX_GAP_PCT:
            return None
        
        gap_type = "GAP_UP" if gap_pct > 0 else "GAP_DOWN"
        
        # Calculate metrics
        volume = df['Volume'].iloc[-1]
        avg_volume = df['Volume'].tail(20).mean()
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1
        
        # ATR
        high = df['High']
        low = df['Low']
        close = df['Close']
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        atr = tr.tail(14).mean()
        atr_ratio = abs(open_price - prev_close) / atr if atr > 0 else 1
        
        # VWAP check (simplified)
        vwap = (df['Close'] * df['Volume']).tail(20).sum() / df['Volume'].tail(20).sum()
        above_vwap = current_price > vwap
        
        # Check if gap filled
        if gap_type == "GAP_UP":
            gap_filled = df['Low'].iloc[-1] <= prev_close
        else:
            gap_filled = df['High'].iloc[-1] >= prev_close
        
        # Calculate score
        score = self._calculate_score(gap_pct, volume_ratio, atr_ratio, above_vwap, gap_filled)
        
        # Determine signal
        signal = self._determine_signal(gap_type, gap_pct, volume_ratio, atr_ratio, above_vwap, gap_filled)
        
        return GapStock(
            symbol=symbol,
            gap_pct=gap_pct,
            gap_type=gap_type,
            prev_close=prev_close,
            open_price=open_price,
            current_price=current_price,
            volume_ratio=volume_ratio,
            atr_ratio=atr_ratio,
            above_vwap=above_vwap,
            gap_filled=gap_filled,
            score=score,
            signal=signal
        )
    
    def _calculate_score(self, gap_pct: float, volume_ratio: float, 
                        atr_ratio: float, above_vwap: bool, gap_filled: bool) -> int:
        """Calculate gap trade score"""
        score = 0
        
        # Gap size (optimal 2-5%)
        gap_abs = abs(gap_pct)
        if 0.02 <= gap_abs <= 0.05:
            score += 20
        elif 0.05 < gap_abs <= 0.08:
            score += 15
        elif gap_abs > 0.08:
            score += 10
        
        # Volume confirmation
        if volume_ratio >= 3:
            score += 20
        elif volume_ratio >= 2:
            score += 15
        elif volume_ratio >= 1.5:
            score += 10
        
        # ATR ratio
        if 1 <= atr_ratio <= 2:
            score += 20
        elif 2 < atr_ratio <= 3:
            score += 15
        elif atr_ratio > 3:
            score += 5  # Overextended
        
        # VWAP position
        if above_vwap and gap_pct > 0:
            score += 20
        elif not above_vwap and gap_pct < 0:
            score += 20
        
        # Gap integrity
        if not gap_filled:
            score += 20
        else:
            score += 5  # Filled = potential fade
        
        return score
    
    def _determine_signal(self, gap_type: str, gap_pct: float, volume_ratio: float,
                         atr_ratio: float, above_vwap: bool, gap_filled: bool) -> str:
        """Determine trading signal"""
        # Gap & Go conditions
        if gap_type == "GAP_UP":
            if volume_ratio >= 2 and above_vwap and not gap_filled and atr_ratio <= 3:
                return "LONG"
        else:  # GAP_DOWN
            if volume_ratio >= 2 and not above_vwap and not gap_filled and atr_ratio <= 3:
                return "SHORT"
        
        # Fade conditions
        if gap_filled and atr_ratio > 2.5:
            return "FADE"
        
        if atr_ratio > 3.5 and volume_ratio < 1.5:
            return "FADE"
        
        return "AVOID"
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch price data"""
        try:
            df = yf.download(symbol, period='25d', progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            self._cache[symbol] = df
            return df
        except:
            return None


# Global instance
_scanner = None

def get_gap_scanner() -> GapScanner:
    global _scanner
    if _scanner is None:
        _scanner = GapScanner()
    return _scanner


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing GapScanner...")
    
    # Test with some popular stocks
    test_symbols = ['AAPL', 'TSLA', 'NVDA', 'AMD', 'META', 'GOOGL', 'AMZN', 'MSFT']
    
    scanner = GapScanner()
    result = scanner.scan(test_symbols)
    
    print(f"\n{'='*50}")
    print("GAP SCAN RESULTS")
    print('='*50)
    print(f"Scan Time: {result.scan_time}")
    print(f"Market Bias: {result.market_bias}")
    print(f"Gap Ups: {len(result.gap_ups)}")
    print(f"Gap Downs: {len(result.gap_downs)}")
    
    if result.gap_ups:
        print("\nTop Gap Ups:")
        for g in result.gap_ups[:3]:
            print(f"  {g.symbol}: {g.gap_pct:+.1%} | Vol: {g.volume_ratio:.1f}x | Score: {g.score} | {g.signal}")
    
    if result.gap_downs:
        print("\nTop Gap Downs:")
        for g in result.gap_downs[:3]:
            print(f"  {g.symbol}: {g.gap_pct:+.1%} | Vol: {g.volume_ratio:.1f}x | Score: {g.score} | {g.signal}")
    
    print(f"\nBest Long Candidates: {[g.symbol for g in result.best_long_candidates]}")
    print(f"Best Short Candidates: {[g.symbol for g in result.best_short_candidates]}")
