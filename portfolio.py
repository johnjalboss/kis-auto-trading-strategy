"""
Portfolio Optimizer
====================
Optimize position sizing and correlation management.

Features:
1. Mean-Variance Optimization (Markowitz)
2. Risk Parity
3. Correlation filtering
4. Maximum diversification
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class PortfolioAllocation:
    """Portfolio allocation result"""
    symbol: str
    weight: float  # 0-1
    expected_return: float
    volatility: float
    sharpe_contribution: float


@dataclass
class OptimizedPortfolio:
    """Optimized portfolio result"""
    allocations: List[PortfolioAllocation]
    total_expected_return: float
    total_volatility: float
    sharpe_ratio: float
    diversification_ratio: float
    
    # Correlation info
    max_correlation: float
    highly_correlated_pairs: List[Tuple[str, str, float]]


class PortfolioOptimizer:
    """
    Portfolio Optimization Engine
    
    Methods:
    1. Equal Weight - Simple baseline
    2. Inverse Volatility - Lower vol = higher weight
    3. Risk Parity - Equal risk contribution
    4. Max Sharpe - Maximize Sharpe ratio
    
    Constraints:
    - Maximum correlation: 0.7 (filter out highly correlated)
    - Maximum single position: 30%
    - Minimum position: 5%
    """
    
    MAX_CORRELATION = 0.7
    MAX_SINGLE_WEIGHT = 0.30
    MIN_WEIGHT = 0.05
    
    def __init__(self, lookback: int = 60):
        self.lookback = lookback
        self._returns_cache: Dict[str, pd.Series] = {}
    
    def optimize(self, symbols: List[str], 
                method: str = "risk_parity",
                total_capital: float = 10000) -> OptimizedPortfolio:
        """
        Optimize portfolio allocation
        
        Args:
            symbols: List of stock symbols
            method: Optimization method
            total_capital: Total capital to allocate
        """
        if len(symbols) == 0:
            return self._empty_portfolio()
        
        if len(symbols) == 1:
            return self._single_stock_portfolio(symbols[0])
        
        # Fetch returns data
        returns_df = self._fetch_returns(symbols)
        
        if returns_df.empty or len(returns_df.columns) < 2:
            return self._equal_weight_fallback(symbols)
        
        # Filter highly correlated pairs
        filtered_symbols = self._filter_correlations(returns_df)
        
        if len(filtered_symbols) < 2:
            filtered_symbols = symbols[:3]  # Keep at least 3
        
        returns_df = returns_df[filtered_symbols]
        
        # Calculate covariance matrix
        cov_matrix = returns_df.cov() * 252  # Annualized
        expected_returns = returns_df.mean() * 252
        volatilities = returns_df.std() * np.sqrt(252)
        
        # Calculate weights based on method
        if method == "equal_weight":
            weights = self._equal_weight(filtered_symbols)
        elif method == "inverse_vol":
            weights = self._inverse_volatility(volatilities)
        elif method == "risk_parity":
            weights = self._risk_parity(cov_matrix)
        elif method == "max_sharpe":
            weights = self._max_sharpe(expected_returns, cov_matrix)
        else:
            weights = self._equal_weight(filtered_symbols)
        
        # Apply constraints
        weights = self._apply_constraints(weights)
        
        # Build allocations
        allocations = []
        for i, symbol in enumerate(filtered_symbols):
            alloc = PortfolioAllocation(
                symbol=symbol,
                weight=weights[i],
                expected_return=expected_returns[symbol],
                volatility=volatilities[symbol],
                sharpe_contribution=weights[i] * expected_returns[symbol] / volatilities[symbol]
            )
            allocations.append(alloc)
        
        # Sort by weight
        allocations.sort(key=lambda x: x.weight, reverse=True)
        
        # Calculate portfolio metrics
        port_return = np.sum(weights * expected_returns.values)
        port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix.values, weights)))
        sharpe = port_return / port_vol if port_vol > 0 else 0
        
        # Diversification ratio
        weighted_vol = np.sum(weights * volatilities.values)
        div_ratio = weighted_vol / port_vol if port_vol > 0 else 1
        
        # Get correlation info
        corr_matrix = returns_df.corr()
        max_corr, high_pairs = self._find_high_correlations(corr_matrix)
        
        return OptimizedPortfolio(
            allocations=allocations,
            total_expected_return=port_return,
            total_volatility=port_vol,
            sharpe_ratio=sharpe,
            diversification_ratio=div_ratio,
            max_correlation=max_corr,
            highly_correlated_pairs=high_pairs
        )
    
    def _fetch_returns(self, symbols: List[str]) -> pd.DataFrame:
        """Fetch daily returns for all symbols"""
        returns_dict = {}
        
        for symbol in symbols:
            try:
                if symbol in self._returns_cache:
                    returns_dict[symbol] = self._returns_cache[symbol]
                else:
                    df = yf.download(symbol, period=f"{self.lookback + 10}d",
                                    progress=False, auto_adjust=True)
                    if not df.empty:
                        close = df['Close']
                        if isinstance(close, pd.DataFrame):
                            close = close.iloc[:, 0]
                        returns = close.pct_change().dropna()
                        returns_dict[symbol] = returns
                        self._returns_cache[symbol] = returns
            except:
                continue
        
        if not returns_dict:
            return pd.DataFrame()
        
        return pd.DataFrame(returns_dict).dropna()
    
    def _filter_correlations(self, returns_df: pd.DataFrame) -> List[str]:
        """Filter out highly correlated stocks"""
        corr_matrix = returns_df.corr()
        symbols = list(returns_df.columns)
        
        to_remove = set()
        
        for i in range(len(symbols)):
            for j in range(i+1, len(symbols)):
                if abs(corr_matrix.iloc[i, j]) > self.MAX_CORRELATION:
                    # Remove the one with lower Sharpe
                    ret_i = returns_df[symbols[i]].mean() / returns_df[symbols[i]].std()
                    ret_j = returns_df[symbols[j]].mean() / returns_df[symbols[j]].std()
                    
                    if ret_i < ret_j:
                        to_remove.add(symbols[i])
                    else:
                        to_remove.add(symbols[j])
        
        return [s for s in symbols if s not in to_remove]
    
    def _equal_weight(self, symbols: List[str]) -> np.ndarray:
        """Equal weight allocation"""
        n = len(symbols)
        return np.array([1/n] * n)
    
    def _inverse_volatility(self, volatilities: pd.Series) -> np.ndarray:
        """Inverse volatility weighting"""
        inv_vol = 1 / volatilities
        return (inv_vol / inv_vol.sum()).values
    
    def _risk_parity(self, cov_matrix: pd.DataFrame) -> np.ndarray:
        """Risk parity allocation (equal risk contribution)"""
        n = len(cov_matrix)
        
        # Start with equal weights
        weights = np.array([1/n] * n)
        
        # Iterative optimization
        for _ in range(100):
            # Marginal risk contribution
            port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix.values, weights)))
            marginal_contrib = np.dot(cov_matrix.values, weights) / port_vol
            risk_contrib = weights * marginal_contrib
            
            # Target risk contribution (equal)
            target_contrib = port_vol / n
            
            # Adjust weights
            for i in range(n):
                weights[i] *= target_contrib / risk_contrib[i] if risk_contrib[i] > 0 else 1
            
            # Normalize
            weights = weights / weights.sum()
        
        return weights
    
    def _max_sharpe(self, returns: pd.Series, cov_matrix: pd.DataFrame) -> np.ndarray:
        """Maximum Sharpe ratio (simplified gradient approach)"""
        n = len(returns)
        
        # Start with equal weights
        weights = np.array([1/n] * n)
        
        best_sharpe = -np.inf
        best_weights = weights.copy()
        
        # Simple gradient search
        for _ in range(1000):
            # Random perturbation
            delta = np.random.randn(n) * 0.01
            new_weights = weights + delta
            new_weights = np.maximum(new_weights, 0.01)
            new_weights = new_weights / new_weights.sum()
            
            # Calculate Sharpe
            port_ret = np.sum(new_weights * returns.values)
            port_vol = np.sqrt(np.dot(new_weights.T, np.dot(cov_matrix.values, new_weights)))
            sharpe = port_ret / port_vol if port_vol > 0 else 0
            
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_weights = new_weights.copy()
                weights = new_weights
        
        return best_weights
    
    def _apply_constraints(self, weights: np.ndarray) -> np.ndarray:
        """Apply min/max weight constraints"""
        # Cap maximum
        weights = np.minimum(weights, self.MAX_SINGLE_WEIGHT)
        
        # Set minimum (if above threshold)
        mask = weights > self.MIN_WEIGHT / 2
        weights[~mask] = 0
        
        # Renormalize
        if weights.sum() > 0:
            weights = weights / weights.sum()
        
        return weights
    
    def _find_high_correlations(self, corr_matrix: pd.DataFrame) -> Tuple[float, List]:
        """Find highly correlated pairs"""
        symbols = list(corr_matrix.columns)
        max_corr = 0
        pairs = []
        
        for i in range(len(symbols)):
            for j in range(i+1, len(symbols)):
                corr = abs(corr_matrix.iloc[i, j])
                if corr > max_corr:
                    max_corr = corr
                if corr > 0.5:
                    pairs.append((symbols[i], symbols[j], corr))
        
        pairs.sort(key=lambda x: x[2], reverse=True)
        return max_corr, pairs[:3]
    
    def _empty_portfolio(self) -> OptimizedPortfolio:
        """Return empty portfolio"""
        return OptimizedPortfolio(
            allocations=[], total_expected_return=0, total_volatility=0,
            sharpe_ratio=0, diversification_ratio=1, max_correlation=0,
            highly_correlated_pairs=[]
        )
    
    def _single_stock_portfolio(self, symbol: str) -> OptimizedPortfolio:
        """Single stock portfolio"""
        alloc = PortfolioAllocation(
            symbol=symbol, weight=1.0, expected_return=0,
            volatility=0, sharpe_contribution=0
        )
        return OptimizedPortfolio(
            allocations=[alloc], total_expected_return=0, total_volatility=0,
            sharpe_ratio=0, diversification_ratio=1, max_correlation=0,
            highly_correlated_pairs=[]
        )
    
    def _equal_weight_fallback(self, symbols: List[str]) -> OptimizedPortfolio:
        """Fallback to equal weight"""
        n = len(symbols)
        allocations = [
            PortfolioAllocation(s, 1/n, 0, 0, 0) for s in symbols
        ]
        return OptimizedPortfolio(
            allocations=allocations, total_expected_return=0, total_volatility=0,
            sharpe_ratio=0, diversification_ratio=1, max_correlation=0,
            highly_correlated_pairs=[]
        )


# Global instance
_optimizer = None

def get_portfolio_optimizer() -> PortfolioOptimizer:
    global _optimizer
    if _optimizer is None:
        _optimizer = PortfolioOptimizer()
    return _optimizer


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing PortfolioOptimizer...")
    
    optimizer = PortfolioOptimizer()
    
    symbols = ["AAPL", "MSFT", "GOOGL", "NVDA", "AMD", "TSLA"]
    
    for method in ["equal_weight", "inverse_vol", "risk_parity"]:
        print(f"\n{'='*50}")
        print(f"Method: {method.upper()}")
        print('='*50)
        
        result = optimizer.optimize(symbols, method=method)
        
        print(f"Expected Return: {result.total_expected_return:.1%}")
        print(f"Volatility: {result.total_volatility:.1%}")
        print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"Diversification: {result.diversification_ratio:.2f}")
        print()
        print("Allocations:")
        for alloc in result.allocations:
            print(f"  {alloc.symbol}: {alloc.weight:.1%}")
        
        if result.highly_correlated_pairs:
            print(f"\nCorrelated Pairs:")
            for s1, s2, corr in result.highly_correlated_pairs:
                print(f"  {s1}-{s2}: {corr:.2f}")
