"""
Correlation Matrix & Diversification
=======================================
Monitor portfolio correlation for optimal diversification.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class CorrelationResult:
    # Portfolio metrics
    avg_correlation: float
    max_correlation: float
    diversification_score: int  # 0-100 (higher = better)
    
    # Highly correlated pairs
    high_corr_pairs: List[tuple]  # (sym1, sym2, corr)
    
    # Recommendations
    too_concentrated: bool
    reduce_positions: List[str]
    add_diversifiers: List[str]
    
    details: List[str]


class CorrelationMonitor:
    """
    Portfolio Correlation Monitor
    
    Goals:
    - Keep avg correlation < 0.6
    - No pair > 0.85
    - Add uncorrelated assets
    """
    
    # Low-correlation assets
    DIVERSIFIERS = ["GLD", "TLT", "UUP", "VNQ", "XLU"]
    
    def __init__(self):
        pass
    
    def analyze(self, symbols: List[str], lookback: int = 60) -> CorrelationResult:
        if len(symbols) < 2:
            return self._default_result()
        
        # Fetch data
        prices = {}
        for sym in symbols:
            df = self._fetch_data(sym, lookback)
            if df is not None and len(df) > 20:
                prices[sym] = df['Close']
        
        if len(prices) < 2:
            return self._default_result()
        
        # Build DataFrame
        price_df = pd.DataFrame(prices)
        returns = price_df.pct_change().dropna()
        
        # Correlation matrix
        corr_matrix = returns.corr()
        
        # Get upper triangle (exclude diagonal)
        upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
        corr_values = upper.stack().values
        
        avg_corr = float(np.mean(corr_values))
        max_corr = float(np.max(corr_values))
        
        # Find high correlation pairs
        high_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                corr = corr_matrix.iloc[i, j]
                if corr > 0.7:
                    high_pairs.append((corr_matrix.columns[i], 
                                      corr_matrix.columns[j], 
                                      round(corr, 2)))
        
        high_pairs.sort(key=lambda x: x[2], reverse=True)
        
        # Diversification score
        div_score = int(max(0, 100 - avg_corr * 100))
        
        # Recommendations
        too_concentrated = avg_corr > 0.6 or max_corr > 0.85
        
        reduce = []
        if high_pairs:
            reduce = [p[0] for p in high_pairs[:2]]
        
        add = [d for d in self.DIVERSIFIERS if d not in symbols][:3]
        
        details = []
        if too_concentrated:
            details.append("⚠️ TOO_CONCENTRATED")
        details.append(f"AVG_CORR:{avg_corr:.2f}")
        
        return CorrelationResult(
            avg_correlation=avg_corr,
            max_correlation=max_corr,
            diversification_score=div_score,
            high_corr_pairs=high_pairs[:5],
            too_concentrated=too_concentrated,
            reduce_positions=reduce,
            add_diversifiers=add,
            details=details
        )
    
    def _fetch_data(self, symbol: str, days: int) -> Optional[pd.DataFrame]:
        try:
            df = yf.download(symbol, period=f'{days}d', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return None
    
    def _default_result(self) -> CorrelationResult:
        return CorrelationResult(0, 0, 100, [], False, [], [], [])


def get_correlation_monitor() -> CorrelationMonitor:
    return CorrelationMonitor()


if __name__ == "__main__":
    print("Testing CorrelationMonitor...")
    c = CorrelationMonitor()
    result = c.analyze(["AAPL", "MSFT", "GOOGL", "NVDA", "AMD"])
    print(f"Avg Corr: {result.avg_correlation:.2f}")
    print(f"Max Corr: {result.max_correlation:.2f}")
    print(f"Diversification: {result.diversification_score}")
    print(f"High Pairs: {result.high_corr_pairs}")
    print(f"Add: {result.add_diversifiers}")
