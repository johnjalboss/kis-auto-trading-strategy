"""
Statistical Arbitrage Engine
==============================
Detect mean-reversion and relative value opportunities.

Strategies:
1. Pairs Trading (cointegration)
2. Z-Score Mean Reversion
3. Sector Relative Strength
4. Beta-Adjusted Spreads
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class PairSignal:
    """Pairs trading signal"""
    stock1: str
    stock2: str
    spread_zscore: float
    hedge_ratio: float
    signal: str  # "LONG_1_SHORT_2", "SHORT_1_LONG_2", "NEUTRAL"
    strength: int


@dataclass
class StatArbSignal:
    """Statistical arbitrage analysis"""
    symbol: str
    
    # Mean reversion
    zscore_10d: float
    zscore_20d: float
    mean_reversion_signal: str
    days_to_mean: int
    
    # Pairs
    best_pair: Optional[PairSignal]
    correlation: float
    
    # Sector relative
    sector: str
    sector_zscore: float
    outperforming: bool
    
    # Beta analysis
    beta: float
    alpha: float
    
    # Combined
    stat_arb_score: int  # -100 to +100
    strategy: str
    details: List[str]


class StatArbEngine:
    """
    Statistical Arbitrage & Mean Reversion
    
    Mean Reversion Rules:
    - Z-score > +2: Oversold territory, potential short
    - Z-score < -2: Oversold territory, potential long
    - Best when combined with fundamentals
    
    Pairs Trading:
    1. Find correlated pairs
    2. Calculate spread z-score
    3. Enter when z-score extreme
    4. Exit when z-score normalizes
    
    Scoring:
    - Z-score < -2 (oversold): +40
    - Z-score > +2 (overbought): -30
    - Strong pair signal: +25
    """
    
    # Common pairs
    PAIRS = [
        ("AAPL", "MSFT"),
        ("GOOGL", "META"),
        ("XOM", "CVX"),
        ("JPM", "BAC"),
        ("HD", "LOW"),
        ("KO", "PEP"),
        ("V", "MA"),
    ]
    
    def __init__(self):
        self._cache: Dict[str, pd.DataFrame] = {}
    
    def analyze(self, symbol: str) -> StatArbSignal:
        """Analyze stat arb opportunities"""
        details = []
        score = 0
        
        df = self._fetch_data(symbol)
        spy = self._fetch_data("SPY")
        
        if df is None or len(df) < 30:
            return self._neutral_result(symbol)
        
        close = df['Close']
        returns = close.pct_change().dropna()
        
        # 1. Mean Reversion Z-Scores
        zscore_10d = self._calculate_zscore(close, 10)
        zscore_20d = self._calculate_zscore(close, 20)
        
        if zscore_20d < -2:
            mean_rev_signal = "OVERSOLD_LONG"
            score += 40
            details.append(f"OVERSOLD:Z={zscore_20d:.2f}")
            days_to_mean = self._estimate_reversion_days(close)
        elif zscore_20d > 2:
            mean_rev_signal = "OVERBOUGHT_SHORT"
            score -= 30
            details.append(f"OVERBOUGHT:Z={zscore_20d:.2f}")
            days_to_mean = self._estimate_reversion_days(close)
        elif abs(zscore_20d) > 1.5:
            mean_rev_signal = "STRETCHED"
            score += 10 if zscore_20d < 0 else -10
            days_to_mean = 5
        else:
            mean_rev_signal = "NEUTRAL"
            days_to_mean = 0
        
        # 2. Find Best Pair
        best_pair = self._find_best_pair(symbol)
        if best_pair:
            correlation = best_pair.correlation if hasattr(best_pair, 'correlation') else 0.8
            if abs(best_pair.spread_zscore) > 2:
                score += 25
                details.append(f"PAIR_SIGNAL:{best_pair.signal}")
        else:
            correlation = 0
        
        # 3. Sector Relative Strength
        sector = self._get_sector(symbol)
        sector_zscore = self._calculate_sector_relative(symbol, sector)
        
        outperforming = sector_zscore > 0.5
        if outperforming:
            score += 10
        
        # 4. Beta and Alpha
        if spy is not None and len(spy) > 30:
            spy_returns = spy['Close'].pct_change().dropna()
            beta, alpha = self._calculate_beta_alpha(returns, spy_returns)
        else:
            beta, alpha = 1.0, 0.0
        
        # High alpha is good
        if alpha > 0.002:  # Positive alpha
            score += 15
            details.append(f"ALPHA_POSITIVE:{alpha*252:.1%}")
        
        # Strategy
        if score >= 40:
            strategy = "MEAN_REVERSION_BUY"
        elif score >= 20:
            strategy = "ACCUMULATE"
        elif score <= -30:
            strategy = "MEAN_REVERSION_SELL"
        elif score <= -10:
            strategy = "REDUCE"
        else:
            strategy = "HOLD"
        
        return StatArbSignal(
            symbol=symbol,
            zscore_10d=zscore_10d,
            zscore_20d=zscore_20d,
            mean_reversion_signal=mean_rev_signal,
            days_to_mean=days_to_mean,
            best_pair=best_pair,
            correlation=correlation,
            sector=sector,
            sector_zscore=sector_zscore,
            outperforming=outperforming,
            beta=beta,
            alpha=alpha,
            stat_arb_score=max(-100, min(100, score)),
            strategy=strategy,
            details=details
        )
    
    def _calculate_zscore(self, series: pd.Series, window: int) -> float:
        """Calculate z-score"""
        mean = series.tail(window).mean()
        std = series.tail(window).std()
        current = series.iloc[-1]
        
        if std > 0:
            return (current - mean) / std
        return 0
    
    def _estimate_reversion_days(self, series: pd.Series) -> int:
        """Estimate days to mean reversion"""
        # Half-life estimation (simplified)
        return 5  # Average 5 days for mean reversion
    
    def _find_best_pair(self, symbol: str) -> Optional[PairSignal]:
        """Find best trading pair"""
        for s1, s2 in self.PAIRS:
            if symbol in [s1, s2]:
                other = s2 if symbol == s1 else s1
                
                df1 = self._fetch_data(symbol)
                df2 = self._fetch_data(other)
                
                if df1 is None or df2 is None:
                    continue
                
                # Calculate spread z-score
                spread = df1['Close'] / df2['Close']
                spread_z = self._calculate_zscore(spread, 20)
                
                # Correlation
                corr = df1['Close'].pct_change().corr(df2['Close'].pct_change())
                
                if corr > 0.6:  # Only valid pairs
                    if spread_z > 2:
                        signal = f"SHORT_{symbol}_LONG_{other}"
                    elif spread_z < -2:
                        signal = f"LONG_{symbol}_SHORT_{other}"
                    else:
                        signal = "NEUTRAL"
                    
                    return PairSignal(
                        stock1=symbol,
                        stock2=other,
                        spread_zscore=spread_z,
                        hedge_ratio=1.0,  # Simplified
                        signal=signal,
                        strength=int(abs(spread_z) * 25)
                    )
        
        return None
    
    def _get_sector(self, symbol: str) -> str:
        """Get sector"""
        tech = ["AAPL", "MSFT", "GOOGL", "META", "NVDA", "AMD"]
        finance = ["JPM", "BAC", "GS", "MS", "V", "MA"]
        energy = ["XOM", "CVX", "COP"]
        
        if symbol in tech:
            return "XLK"
        elif symbol in finance:
            return "XLF"
        elif symbol in energy:
            return "XLE"
        return "SPY"
    
    def _calculate_sector_relative(self, symbol: str, sector_etf: str) -> float:
        """Calculate relative strength vs sector"""
        stock = self._fetch_data(symbol)
        sector = self._fetch_data(sector_etf)
        
        if stock is None or sector is None:
            return 0
        
        stock_ret = stock['Close'].pct_change().tail(20).sum()
        sector_ret = sector['Close'].pct_change().tail(20).sum()
        
        return stock_ret - sector_ret
    
    def _calculate_beta_alpha(self, returns: pd.Series, 
                               market_returns: pd.Series) -> Tuple[float, float]:
        """Calculate beta and alpha"""
        # Align data
        aligned = pd.concat([returns, market_returns], axis=1).dropna()
        if len(aligned) < 20:
            return 1.0, 0.0
        
        aligned.columns = ['stock', 'market']
        
        cov = aligned['stock'].cov(aligned['market'])
        var = aligned['market'].var()
        
        beta = cov / var if var > 0 else 1.0
        alpha = aligned['stock'].mean() - beta * aligned['market'].mean()
        
        return float(beta), float(alpha)
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch data"""
        if symbol in self._cache:
            return self._cache[symbol]
        
        try:
            df = yf.download(symbol, period='60d', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            self._cache[symbol] = df
            return df
        except:
            return None
    
    def _neutral_result(self, symbol: str) -> StatArbSignal:
        """Neutral result"""
        return StatArbSignal(
            symbol=symbol, zscore_10d=0, zscore_20d=0,
            mean_reversion_signal="NEUTRAL", days_to_mean=0,
            best_pair=None, correlation=0, sector="SPY", sector_zscore=0,
            outperforming=False, beta=1.0, alpha=0,
            stat_arb_score=0, strategy="HOLD", details=[]
        )


# Global
_engine = None

def get_stat_arb_engine() -> StatArbEngine:
    global _engine
    if _engine is None:
        _engine = StatArbEngine()
    return _engine


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing StatArbEngine...")
    
    engine = StatArbEngine()
    
    for symbol in ["AAPL", "NVDA"]:
        print(f"\n{'='*60}")
        print(f"{symbol}")
        print('='*60)
        
        result = engine.analyze(symbol)
        
        print(f"Signal: {result.mean_reversion_signal}")
        print(f"Z-Score (20d): {result.zscore_20d:.2f}")
        print(f"Strategy: {result.strategy}")
        print(f"Score: {result.stat_arb_score:+d}")
        print()
        print(f"Beta: {result.beta:.2f} | Alpha: {result.alpha*252:.2%}")
        print(f"Sector: {result.sector} (Z: {result.sector_zscore:+.2f})")
        if result.best_pair:
            print(f"Pair: {result.best_pair.stock2} (Spread Z: {result.best_pair.spread_zscore:.2f})")
        print(f"Details: {result.details}")
