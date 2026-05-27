"""
Tail Risk & Black Swan Protection
====================================
Detect and protect against extreme market events.

Metrics:
1. VaR (Value at Risk)
2. CVaR (Conditional VaR)
3. Maximum Drawdown Risk
4. Tail Event Probability
5. Crisis Indicators
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class TailRiskSignal:
    """Tail risk analysis"""
    # Portfolio metrics
    var_95: float          # 95% VaR (1-day)
    var_99: float          # 99% VaR
    cvar_95: float         # Expected Shortfall
    
    # Drawdown risk
    max_dd_20d: float      # Max DD last 20 days
    current_dd: float
    dd_recovery_days: int
    
    # Tail probability
    crash_probability: float  # P(drop > 5% in 1 day)
    tail_regime: str         # "NORMAL", "ELEVATED", "EXTREME"
    
    # Crisis indicators
    correlation_spike: bool
    volatility_cluster: bool
    liquidity_stress: bool
    
    # Protection
    hedge_recommendation: str
    protection_level: float  # % to hedge
    
    risk_score: int  # -100 (dangerous) to +100 (safe)
    details: List[str]


class TailRiskAnalyzer:
    """
    Tail Risk & Black Swan Protection
    
    Key Indicators:
    1. VaR/CVaR - Expected losses
    2. Correlation spike - All assets fall together
    3. Volatility clustering - Bad days cluster
    4. Liquidity stress - Wide spreads
    
    Protection Strategies:
    - NORMAL: Standard position sizing
    - ELEVATED: Reduce exposure 30%
    - EXTREME: Hedge or go cash
    
    Scoring:
    - Normal tail risk: +30
    - Elevated tail: -20
    - Extreme/Crisis: -50
    - Correlation spike: -25
    """
    
    def __init__(self):
        pass
    
    def analyze(self, symbols: List[str] = None) -> TailRiskSignal:
        """Analyze tail risk"""
        details = []
        score = 30  # Start optimistic
        
        if symbols is None:
            symbols = ["SPY"]
        
        # Fetch SPY for market risk
        spy = self._fetch_data("SPY")
        vix = self._fetch_data("^VIX")
        
        if spy is None or len(spy) < 30:
            return self._default_result()
        
        returns = spy['Close'].pct_change().dropna()
        
        # 1. VaR Calculation
        var_95 = self._calculate_var(returns, 0.05)
        var_99 = self._calculate_var(returns, 0.01)
        cvar_95 = self._calculate_cvar(returns, 0.05)
        
        # 2. Drawdown Analysis
        close = spy['Close']
        rolling_max = close.rolling(252, min_periods=1).max()
        drawdown = (close - rolling_max) / rolling_max
        
        current_dd = float(drawdown.iloc[-1])
        max_dd_20d = float(drawdown.tail(20).min())
        
        # Estimate recovery days
        if current_dd < -0.05:
            dd_recovery = int(abs(current_dd) / 0.005)  # ~0.5% per day recovery
        else:
            dd_recovery = 0
        
        # 3. Tail Probability (fat tail estimation)
        # Count historical 5%+ drops
        big_drops = (returns < -0.05).sum()
        crash_prob = big_drops / len(returns)
        
        # Adjust for current volatility
        vix_level = float(vix['Close'].iloc[-1]) if vix is not None and not vix.empty else 20
        if vix_level > 30:
            crash_prob *= 2
        
        # 4. Tail Regime
        if vix_level > 35 or crash_prob > 0.05:
            tail_regime = "EXTREME"
            score -= 50
            details.append("⚠️ EXTREME_TAIL_RISK")
        elif vix_level > 25 or crash_prob > 0.03:
            tail_regime = "ELEVATED"
            score -= 20
            details.append("ELEVATED_TAIL_RISK")
        else:
            tail_regime = "NORMAL"
            details.append("NORMAL_TAIL")
        
        # 5. Correlation Spike Detection
        # When correlations go to 1, diversification fails
        correlation_spike = self._detect_correlation_spike()
        if correlation_spike:
            score -= 25
            details.append("CORRELATION_SPIKE")
        
        # 6. Volatility Clustering
        vol_20 = returns.tail(20).std()
        vol_60 = returns.tail(60).std()
        volatility_cluster = vol_20 > vol_60 * 1.5
        
        if volatility_cluster:
            score -= 15
            details.append("VOL_CLUSTERING")
        
        # 7. Liquidity Stress (simplified)
        liquidity_stress = vix_level > 30
        if liquidity_stress:
            details.append("LIQUIDITY_STRESS")
        
        # 8. Protection Recommendation
        if tail_regime == "EXTREME":
            hedge_rec = "FULL_HEDGE_OR_CASH"
            protection = 0.50
        elif tail_regime == "ELEVATED":
            hedge_rec = "PARTIAL_HEDGE"
            protection = 0.30
        elif current_dd < -0.10:
            hedge_rec = "CONSIDER_HEDGE"
            protection = 0.20
        else:
            hedge_rec = "NORMAL_OPERATIONS"
            protection = 0.05
        
        return TailRiskSignal(
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            max_dd_20d=max_dd_20d,
            current_dd=current_dd,
            dd_recovery_days=dd_recovery,
            crash_probability=crash_prob,
            tail_regime=tail_regime,
            correlation_spike=correlation_spike,
            volatility_cluster=volatility_cluster,
            liquidity_stress=liquidity_stress,
            hedge_recommendation=hedge_rec,
            protection_level=protection,
            risk_score=max(-100, min(100, score)),
            details=details
        )
    
    def _calculate_var(self, returns: pd.Series, alpha: float) -> float:
        """Calculate Value at Risk"""
        return float(np.percentile(returns, alpha * 100))
    
    def _calculate_cvar(self, returns: pd.Series, alpha: float) -> float:
        """Calculate Conditional VaR (Expected Shortfall)"""
        var = self._calculate_var(returns, alpha)
        return float(returns[returns <= var].mean())
    
    def _detect_correlation_spike(self) -> bool:
        """Detect if correlations are spiking"""
        # Fetch multiple assets
        assets = ["SPY", "TLT", "GLD", "UUP"]
        dfs = {}
        
        for asset in assets:
            df = self._fetch_data(asset)
            if df is not None and not df.empty:
                dfs[asset] = df['Close'].pct_change()
        
        if len(dfs) < 3:
            return False
        
        # Calculate recent correlations
        combined = pd.DataFrame(dfs).dropna()
        if len(combined) < 20:
            return False
        
        recent_corr = combined.tail(10).corr()
        
        # Average absolute correlation
        corr_values = recent_corr.values[np.triu_indices(len(recent_corr), 1)]
        avg_abs_corr = np.abs(corr_values).mean()
        
        # Spike if avg correlation > 0.7
        return avg_abs_corr > 0.7
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch data"""
        try:
            df = yf.download(symbol, period='1y', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return None
    
    def _default_result(self) -> TailRiskSignal:
        """Default result"""
        return TailRiskSignal(
            var_95=-0.02, var_99=-0.03, cvar_95=-0.035,
            max_dd_20d=-0.05, current_dd=-0.02, dd_recovery_days=5,
            crash_probability=0.01, tail_regime="NORMAL",
            correlation_spike=False, volatility_cluster=False, liquidity_stress=False,
            hedge_recommendation="NORMAL_OPERATIONS", protection_level=0.05,
            risk_score=30, details=[]
        )


# Global
_analyzer = None

def get_tail_risk_analyzer() -> TailRiskAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = TailRiskAnalyzer()
    return _analyzer


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing TailRiskAnalyzer...")
    
    analyzer = TailRiskAnalyzer()
    result = analyzer.analyze()
    
    print(f"\n{'='*60}")
    print("TAIL RISK ANALYSIS")
    print('='*60)
    print(f"Tail Regime: {result.tail_regime}")
    print(f"Risk Score: {result.risk_score:+d}")
    print()
    print(f"VaR (95%): {result.var_95:.2%}")
    print(f"VaR (99%): {result.var_99:.2%}")
    print(f"CVaR (95%): {result.cvar_95:.2%}")
    print()
    print(f"Current DD: {result.current_dd:.2%}")
    print(f"Max DD (20d): {result.max_dd_20d:.2%}")
    print(f"Crash Probability: {result.crash_probability:.2%}")
    print()
    print(f"Correlation Spike: {result.correlation_spike}")
    print(f"Vol Clustering: {result.volatility_cluster}")
    print()
    print(f"💡 Recommendation: {result.hedge_recommendation}")
    print(f"📐 Hedge: {result.protection_level:.0%}")
    print(f"Details: {result.details}")
