"""
VIX Structure Analyzer
========================
Analyze VIX term structure for volatility regime insights.

Metrics:
1. Contango vs Backwardation
2. VIX Spread (VIX vs VIX3M)
3. VVIX (Volatility of Volatility)
4. VIX Spike Detection
5. Mean Reversion Signals
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class VixSignal:
    """VIX structure analysis"""
    vix: float
    vix_3m: float
    
    # Structure
    term_structure: str  # "CONTANGO", "BACKWARDATION", "FLAT"
    vix_spread: float    # VIX - VIX3M
    spread_percentile: float
    
    # Levels
    vix_percentile: float
    vix_zscore: float
    
    # Signals
    is_spike: bool
    is_crushed: bool
    mean_reversion_signal: str
    
    # Volatility of volatility
    vvix_level: float
    uncertainty: str  # "LOW", "NORMAL", "HIGH", "EXTREME"
    
    # Trading implications
    vol_regime: str
    strategy: str
    
    vix_score: int  # -100 to +100
    details: List[str]

    @property
    def score(self) -> int:
        return self.vix_score


class VixStructureAnalyzer:
    """
    VIX Term Structure Analysis
    
    Key Insights:
    1. CONTANGO (VIX < VIX3M) = Normal, market complacent
    2. BACKWARDATION (VIX > VIX3M) = Fear, near-term worry
    3. VIX > 30 = High fear, potential bottom
    4. VIX < 12 = Extreme complacency, caution
    
    Trading Strategies:
    - Backwardation + VIX > 30 → Contrarian buy signal
    - Contango + VIX < 13 → Take profits, raise cash
    - VIX spike >40% → Wait 3-5 days for reversion
    
    Scoring:
    - VIX in 15-20, contango: +20 (healthy)
    - VIX > 30 + backwardation: +30 (fear/opportunity)
    - VIX > 35: -20 (too risky)
    - VIX < 12: -25 (complacency danger)
    """
    
    def __init__(self):
        self._cache: Dict[str, pd.DataFrame] = {}
    
    def analyze(self) -> VixSignal:
        """Analyze VIX structure"""
        details = []
        score = 0
        
        # Fetch VIX data
        vix_df = self._fetch_data("^VIX")
        
        if vix_df is None or vix_df.empty:
            return self._default_result()
        
        vix = float(vix_df['Close'].iloc[-1])
        
        # VIX3M (3-month VIX) - use proxy if not available
        vix3m_df = self._fetch_data("^VIX3M")
        if vix3m_df is not None and not vix3m_df.empty:
            vix_3m = float(vix3m_df['Close'].iloc[-1])
        else:
            # Estimate: typically VIX3M is 5-15% higher than VIX in contango
            vix_3m = vix * 1.1
        
        # 1. Term Structure
        vix_spread = vix - vix_3m
        
        if vix_spread < -2:
            term_structure = "CONTANGO"
            details.append("CONTANGO:Normal")
        elif vix_spread > 2:
            term_structure = "BACKWARDATION"
            details.append("BACKWARDATION:Fear")
            score -= 10  # Near-term fear
        else:
            term_structure = "FLAT"
        
        # 2. VIX Level Analysis
        vix_history = vix_df['Close'].tail(252)
        vix_mean = vix_history.mean()
        vix_std = vix_history.std()
        
        vix_percentile = (vix_history < vix).sum() / len(vix_history) * 100
        vix_zscore = (vix - vix_mean) / vix_std if vix_std > 0 else 0
        
        # Spread percentile (historical)
        spread_percentile = 50  # Would need historical spread data
        
        # 3. Spike Detection
        vix_1d_ago = vix_df['Close'].iloc[-2] if len(vix_df) > 1 else vix
        vix_change = (vix / vix_1d_ago - 1) * 100
        
        is_spike = vix_change > 25 or vix > vix_mean + 2 * vix_std
        
        # 4. Mean Reversion Signal
        if vix_zscore > 2:
            mean_reversion = "SELL_VOL"  # VIX likely to fall
            score += 20
            details.append(f"VIX_ELEVATED:{vix:.1f}")
        elif vix_zscore < -1.5:
            mean_reversion = "BUY_VOL"  # VIX likely to rise
            score -= 25
            details.append("VIX_CRUSHED:Complacency")
        else:
            mean_reversion = "NEUTRAL"
        
        # 5. Level-based scoring
        if vix > 35:
            score -= 20
            details.append("EXTREME_FEAR")
            vol_regime = "EXTREME"
        elif vix > 25:
            if term_structure == "BACKWARDATION":
                score += 30  # Contrarian opportunity
                details.append("FEAR_OPPORTUNITY")
            vol_regime = "HIGH"
        elif 15 <= vix <= 20:
            score += 20
            vol_regime = "HEALTHY"
            details.append("HEALTHY_VIX")
        elif vix < 13:
            score -= 25
            vol_regime = "COMPLACENT"
            details.append("DANGER:Complacency")
        else:
            vol_regime = "NORMAL"
        
        # Is crushed?
        is_crushed = vix < 14
        
        # VVIX (volatility of volatility) - estimate
        vvix_level = vix_std / vix_mean * 100 * 5  # Scaled estimate
        
        if vvix_level > 120:
            uncertainty = "EXTREME"
        elif vvix_level > 100:
            uncertainty = "HIGH"
        elif vvix_level > 80:
            uncertainty = "NORMAL"
        else:
            uncertainty = "LOW"
        
        # Strategy recommendation
        if vol_regime == "EXTREME":
            strategy = "CASH_HEDGE"
        elif vol_regime == "HIGH" and term_structure == "BACKWARDATION":
            strategy = "CONTRARIAN_BUY"
        elif vol_regime == "COMPLACENT":
            strategy = "REDUCE_EXPOSURE"
        elif vol_regime == "HEALTHY":
            strategy = "NORMAL_TRADING"
        else:
            strategy = "CAUTIOUS"
        
        return VixSignal(
            vix=vix,
            vix_3m=vix_3m,
            term_structure=term_structure,
            vix_spread=vix_spread,
            spread_percentile=spread_percentile,
            vix_percentile=vix_percentile,
            vix_zscore=vix_zscore,
            is_spike=is_spike,
            is_crushed=is_crushed,
            mean_reversion_signal=mean_reversion,
            vvix_level=vvix_level,
            uncertainty=uncertainty,
            vol_regime=vol_regime,
            strategy=strategy,
            vix_score=max(-100, min(100, score)),
            details=details
        )
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch data"""
        try:
            df = yf.download(symbol, period='1y', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return None
    
    def _default_result(self) -> VixSignal:
        """Default result"""
        return VixSignal(
            vix=20, vix_3m=22, term_structure="CONTANGO",
            vix_spread=-2, spread_percentile=50,
            vix_percentile=50, vix_zscore=0,
            is_spike=False, is_crushed=False, mean_reversion_signal="NEUTRAL",
            vvix_level=90, uncertainty="NORMAL",
            vol_regime="NORMAL", strategy="NORMAL_TRADING",
            vix_score=0, details=[]
        )


# Global
_analyzer = None

def get_vix_analyzer() -> VixStructureAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = VixStructureAnalyzer()
    return _analyzer


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing VixStructureAnalyzer...")
    
    analyzer = VixStructureAnalyzer()
    result = analyzer.analyze()
    
    print(f"\n{'='*60}")
    print("VIX STRUCTURE ANALYSIS")
    print('='*60)
    print(f"VIX: {result.vix:.2f} | VIX3M: {result.vix_3m:.2f}")
    print(f"Term Structure: {result.term_structure}")
    print(f"Spread: {result.vix_spread:+.2f}")
    print()
    print(f"VIX Percentile: {result.vix_percentile:.0f}%")
    print(f"VIX Z-Score: {result.vix_zscore:+.2f}")
    print(f"Is Spike: {result.is_spike}")
    print(f"Is Crushed: {result.is_crushed}")
    print()
    print(f"Mean Reversion: {result.mean_reversion_signal}")
    print(f"Vol Regime: {result.vol_regime}")
    print(f"Strategy: {result.strategy}")
    print(f"Score: {result.vix_score:+d}")
    print(f"Details: {result.details}")


def get_vix_metrics():
    return VixStructureAnalyzer().analyze()
