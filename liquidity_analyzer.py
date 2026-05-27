"""
Liquidity Analyzer
===================
Analyze market liquidity to avoid slippage and detect traps.

Metrics:
1. Bid-Ask Spread Analysis
2. Volume-to-Float Ratio
3. Average Dollar Volume
4. Depth Score
5. Liquidity Risk Assessment
"""

from dataclasses import dataclass
from typing import Optional, Dict, List
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class LiquidityMetrics:
    """Liquidity metrics"""
    symbol: str
    
    # Volume metrics
    avg_daily_volume: float
    avg_dollar_volume: float
    relative_volume: float  # vs 20-day avg
    
    # Float metrics
    float_shares: float
    volume_to_float: float  # Daily turnover
    
    # Spread metrics
    avg_spread_pct: float
    current_spread_pct: float
    
    # Risk metrics
    liquidity_score: int  # 0-100
    slippage_estimate: float  # For $10K order
    
    # Recommendation
    can_trade: bool
    max_position_size: float
    warnings: List[str]


class LiquidityAnalyzer:
    """
    Liquidity Analysis Engine
    
    Scoring:
    - Avg Dollar Volume > $50M: +30 pts
    - Avg Dollar Volume > $20M: +20 pts
    - Avg Dollar Volume > $5M: +10 pts
    
    - Spread < 0.05%: +25 pts
    - Spread < 0.10%: +15 pts
    - Spread < 0.20%: +5 pts
    
    - Relative Volume > 1.5: +10 pts (active)
    - Relative Volume > 2.0: +15 pts (very active)
    
    - Float turnover reasonable: +20 pts
    
    Minimum Score: 50 to trade
    """
    
    MIN_DOLLAR_VOLUME = 1_000_000  # $1M minimum
    MIN_LIQUIDITY_SCORE = 50
    
    def __init__(self):
        self._cache: Dict[str, tuple] = {}
        self._cache_ttl = 3600  # 1 hour
    
    def analyze(self, symbol: str, order_size: float = 10000) -> LiquidityMetrics:
        """Analyze liquidity for a symbol"""
        warnings = []
        
        # Fetch data
        df = self._fetch_data(symbol)
        info = self._fetch_info(symbol)
        
        if df is None or len(df) < 10:
            return self._illiquid_result(symbol)
        
        # Calculate metrics
        close = df['Close'].iloc[-1]
        volume = df['Volume'].iloc[-1]
        avg_volume = df['Volume'].tail(20).mean()
        
        avg_daily_volume = avg_volume
        avg_dollar_volume = avg_volume * close
        relative_volume = volume / avg_volume if avg_volume > 0 else 1
        
        # Float data
        float_shares = info.get('floatShares', 0) or 0
        if float_shares == 0:
            float_shares = info.get('sharesOutstanding', 0) or avg_volume * 10
        
        volume_to_float = avg_volume / float_shares if float_shares > 0 else 0
        
        # Spread estimation (simplified - use bid/ask if available)
        high_low_range = (df['High'] - df['Low']).tail(5).mean()
        avg_spread_pct = (high_low_range / close) * 0.1  # Estimate spread as 10% of range
        avg_spread_pct = max(0.0001, min(0.01, avg_spread_pct))  # Bound between 0.01% and 1%
        
        current_spread_pct = avg_spread_pct  # Current = avg (no real-time bid/ask)
        
        # Calculate liquidity score
        score = 0
        
        # Dollar volume scoring
        if avg_dollar_volume > 50_000_000:
            score += 30
        elif avg_dollar_volume > 20_000_000:
            score += 20
        elif avg_dollar_volume > 5_000_000:
            score += 10
        else:
            warnings.append("LOW_DOLLAR_VOLUME")
        
        # Spread scoring
        if avg_spread_pct < 0.0005:
            score += 25
        elif avg_spread_pct < 0.001:
            score += 15
        elif avg_spread_pct < 0.002:
            score += 5
        else:
            warnings.append("WIDE_SPREAD")
        
        # Relative volume scoring
        if relative_volume > 2.0:
            score += 15
        elif relative_volume > 1.5:
            score += 10
        elif relative_volume > 1.0:
            score += 5
        
        # Float turnover (healthy = 1-10% daily)
        if 0.01 < volume_to_float < 0.10:
            score += 20
        elif 0.005 < volume_to_float < 0.15:
            score += 10
        elif volume_to_float > 0.20:
            warnings.append("HIGH_TURNOVER_RISK")
        elif volume_to_float < 0.005:
            warnings.append("LOW_TURNOVER")
        
        # Estimate slippage
        impact = order_size / avg_dollar_volume if avg_dollar_volume > 0 else 1
        slippage_estimate = avg_spread_pct / 2 + (impact * 0.5)  # Half spread + market impact
        slippage_estimate = min(0.03, slippage_estimate)  # Cap at 3%
        
        # Can trade?
        can_trade = (score >= self.MIN_LIQUIDITY_SCORE and 
                    avg_dollar_volume >= self.MIN_DOLLAR_VOLUME)
        
        # Max position size (1% of daily volume)
        max_position = avg_dollar_volume * 0.01
        
        if not can_trade:
            warnings.append("INSUFFICIENT_LIQUIDITY")
        
        return LiquidityMetrics(
            symbol=symbol,
            avg_daily_volume=avg_daily_volume,
            avg_dollar_volume=avg_dollar_volume,
            relative_volume=relative_volume,
            float_shares=float_shares,
            volume_to_float=volume_to_float,
            avg_spread_pct=avg_spread_pct,
            current_spread_pct=current_spread_pct,
            liquidity_score=min(100, score),
            slippage_estimate=slippage_estimate,
            can_trade=can_trade,
            max_position_size=max_position,
            warnings=warnings
        )
    
    def filter_by_liquidity(self, symbols: List[str], min_score: int = 50) -> List[str]:
        """Filter symbols by liquidity score"""
        liquid_symbols = []
        
        for symbol in symbols:
            metrics = self.analyze(symbol)
            if metrics.liquidity_score >= min_score and metrics.can_trade:
                liquid_symbols.append(symbol)
        
        return liquid_symbols
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch price data"""
        try:
            df = yf.download(symbol, period='30d', progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return None
    
    def _fetch_info(self, symbol: str) -> dict:
        """Fetch stock info"""
        try:
            ticker = yf.Ticker(symbol)
            return ticker.info or {}
        except:
            return {}
    
    def _illiquid_result(self, symbol: str) -> LiquidityMetrics:
        """Return illiquid result"""
        return LiquidityMetrics(
            symbol=symbol, avg_daily_volume=0, avg_dollar_volume=0,
            relative_volume=0, float_shares=0, volume_to_float=0,
            avg_spread_pct=0.01, current_spread_pct=0.01,
            liquidity_score=0, slippage_estimate=0.03,
            can_trade=False, max_position_size=0,
            warnings=["NO_DATA"]
        )


# Global instance
_analyzer = None

def get_liquidity_analyzer() -> LiquidityAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = LiquidityAnalyzer()
    return _analyzer


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing LiquidityAnalyzer...")
    
    analyzer = LiquidityAnalyzer()
    
    for symbol in ["AAPL", "TSLA", "GME", "NVDA"]:
        print(f"\n{'='*50}")
        print(f"{symbol}")
        print('='*50)
        
        result = analyzer.analyze(symbol)
        
        print(f"Can Trade: {'✅' if result.can_trade else '❌'}")
        print(f"Liquidity Score: {result.liquidity_score}")
        print(f"Avg $ Volume: ${result.avg_dollar_volume/1e6:.1f}M")
        print(f"Rel Volume: {result.relative_volume:.1f}x")
        print(f"Spread: {result.avg_spread_pct:.3%}")
        print(f"Slippage (10K): {result.slippage_estimate:.2%}")
        print(f"Max Position: ${result.max_position_size:,.0f}")
        if result.warnings:
            print(f"⚠️ {result.warnings}")
