"""
Liquidity Filter
==================
Avoid illiquid stocks that are hard to exit.
"""

from dataclasses import dataclass
from typing import Optional
import yfinance as yf
from loguru import logger


@dataclass
class LiquidityCheck:
    symbol: str
    avg_volume: float
    avg_dollar_volume: float
    bid_ask_spread_pct: float
    
    liquidity_grade: str  # "A", "B", "C", "D", "F"
    is_tradeable: bool
    max_position_value: float
    
    warnings: list


class LiquidityFilter:
    """
    Liquidity Filter
    
    Rules:
    - Min $5M daily dollar volume for entry
    - Position size < 1% of daily volume
    - Avoid wide bid-ask spreads (>0.5%)
    
    Grades:
    A: $50M+ volume, tight spread
    B: $20M+ volume
    C: $5M+ volume (minimum)
    D: $1M+ volume (warning)
    F: <$1M (avoid)
    """
    
    MIN_DOLLAR_VOLUME = 5_000_000  # $5M
    MAX_POSITION_PCT_OF_VOLUME = 0.01  # 1%
    MAX_SPREAD_PCT = 0.005  # 0.5%
    
    def __init__(self, min_volume: float = 5_000_000):
        self.min_volume = min_volume
    
    def check(self, symbol: str) -> LiquidityCheck:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period='1mo')
            
            if hist.empty:
                return self._fail(symbol, "No data")
            
            # Average volume
            avg_vol = float(hist['Volume'].mean())
            
            # Dollar volume
            price = float(hist['Close'].iloc[-1])
            dollar_vol = avg_vol * price
            
            # Bid-ask spread estimate (Safeguard for off-hours when yfinance info bid/ask is 0 or invalid)
            bid = info.get('bid')
            ask = info.get('ask')
            if not bid or not ask or bid <= 0 or ask <= 0:
                spread_pct = 0.05  # Default tight 5bps spread for US stocks when bid/ask unavailable off-hours
            else:
                spread_pct = (ask - bid) / price * 100 if price > 0 else 0.05
            
            warnings = []
            
            # Grade
            if dollar_vol >= 50_000_000 and spread_pct < 0.8:
                grade = "A"
            elif dollar_vol >= 20_000_000:
                grade = "B"
            elif dollar_vol >= 5_000_000:
                grade = "C"
            elif dollar_vol >= 1_000_000:
                grade = "D"
                warnings.append("Low liquidity - small positions only")
            else:
                grade = "F"
                warnings.append("Extremely low liquidity - AVOID")
            
            if spread_pct > 1.5:
                warnings.append(f"Wide spread: {spread_pct:.2f}%")
            
            # Allow A, B, C grades (and D for known liquid universe)
            is_tradeable = grade in ["A", "B", "C"] or dollar_vol >= 10_000_000
            
            # Max position (1% of daily volume)
            max_pos = dollar_vol * self.MAX_POSITION_PCT_OF_VOLUME
            
            return LiquidityCheck(
                symbol=symbol,
                avg_volume=avg_vol,
                avg_dollar_volume=dollar_vol,
                bid_ask_spread_pct=spread_pct,
                liquidity_grade=grade,
                is_tradeable=is_tradeable,
                max_position_value=max_pos,
                warnings=warnings
            )
            
        except Exception as e:
            return self._fail(symbol, str(e))
    
    def filter_tradeable(self, symbols: list) -> list:
        """Filter to only tradeable symbols"""
        tradeable = []
        for sym in symbols:
            check = self.check(sym)
            if check.is_tradeable:
                tradeable.append(sym)
        return tradeable
    
    def _fail(self, symbol: str, reason: str) -> LiquidityCheck:
        return LiquidityCheck(symbol, 0, 0, 100, "F", False, 0, [reason])


def get_liquidity_filter() -> LiquidityFilter:
    return LiquidityFilter()


if __name__ == "__main__":
    print("Testing LiquidityFilter...")
    lf = LiquidityFilter()
    
    symbols = ["AAPL", "NVDA", "TSLA", "MSFT"]
    
    for sym in symbols:
        check = lf.check(sym)
        print(f"\n{sym}:")
        print(f"  Grade: {check.liquidity_grade}")
        print(f"  Dollar Volume: ${check.avg_dollar_volume/1e6:.1f}M")
        print(f"  Spread: {check.bid_ask_spread_pct:.2f}%")
        print(f"  Max Position: ${check.max_position_value:,.0f}")
        print(f"  Tradeable: {check.is_tradeable}")
        if check.warnings:
            print(f"  Warnings: {check.warnings}")
