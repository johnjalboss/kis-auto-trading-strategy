"""
Credit Spread Analyzer
========================
Analyze credit market stress for risk-off signals.

Metrics:
1. HYG/LQD Ratio - High Yield vs Investment Grade
2. Credit Spread - Corporate vs Treasury
3. Junk Bond Stress
4. Investment Grade Flow
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class CreditSignal:
    """Credit market analysis"""
    # Spreads
    hyg_lqd_ratio: float
    spread_direction: str  # "WIDENING", "TIGHTENING", "STABLE"
    spread_percentile: float
    
    # Stress levels
    credit_stress: str  # "LOW", "NORMAL", "ELEVATED", "HIGH", "CRISIS"
    stress_score: float  # 0-100
    
    # ETF performance
    hyg_return_5d: float
    lqd_return_5d: float
    relative_performance: float
    
    # Risk assessment
    risk_off_signal: bool
    flight_to_quality: bool
    
    # Trading
    credit_score: int  # -100 to +100
    strategy: str
    details: List[str]

    @property
    def score(self) -> int:
        return self.credit_score


class CreditSpreadAnalyzer:
    """
    Credit Market Stress Analysis
    
    Key Relationships:
    - HYG (High Yield) falls before equities in stress
    - LQD (IG Bonds) = Flight to quality
    - HYG/LQD ratio falling = Credit stress
    - Credit leads equity by 1-2 weeks
    
    Signals:
    - HYG underperforming = Risk-off
    - Spreads widening = Caution
    - Flight to quality = Defensive
    
    Scoring:
    - Tight spreads: +30
    - Widening spreads: -40
    - Credit stress: -50
    - Flight to quality: -20
    """
    
    def __init__(self):
        pass
    
    def analyze(self) -> CreditSignal:
        """Analyze credit spreads"""
        details = []
        score = 0
        
        # Fetch ETF data
        hyg = self._fetch_data("HYG")  # High Yield
        lqd = self._fetch_data("LQD")  # Investment Grade
        tlt = self._fetch_data("TLT")  # Treasuries
        
        if hyg is None or lqd is None:
            return self._default_result()
        
        # Calculate ratio
        hyg_close = hyg['Close']
        lqd_close = lqd['Close']
        
        ratio = hyg_close / lqd_close
        current_ratio = float(ratio.iloc[-1])
        ratio_5d_ago = float(ratio.iloc[-5]) if len(ratio) >= 5 else current_ratio
        ratio_20d_ago = float(ratio.iloc[-20]) if len(ratio) >= 20 else current_ratio
        
        # Spread direction
        ratio_change_5d = (current_ratio / ratio_5d_ago - 1) * 100
        
        if ratio_change_5d < -1:
            spread_dir = "WIDENING"
            score -= 30
            details.append("SPREADS_WIDENING")
        elif ratio_change_5d > 1:
            spread_dir = "TIGHTENING"
            score += 25
            details.append("SPREADS_TIGHTENING")
        else:
            spread_dir = "STABLE"
        
        # Percentile
        ratio_min = ratio.min()
        ratio_max = ratio.max()
        percentile = (current_ratio - ratio_min) / (ratio_max - ratio_min) * 100 if (ratio_max - ratio_min) > 0 else 50
        
        # Stress level
        if percentile < 10:
            stress = "CRISIS"
            stress_score = 90
            score -= 60
            details.append("⚠️ CREDIT_CRISIS")
        elif percentile < 25:
            stress = "HIGH"
            stress_score = 70
            score -= 40
            details.append("HIGH_STRESS")
        elif percentile < 40:
            stress = "ELEVATED"
            stress_score = 50
            score -= 20
        elif percentile > 75:
            stress = "LOW"
            stress_score = 20
            score += 30
            details.append("HEALTHY_CREDIT")
        else:
            stress = "NORMAL"
            stress_score = 35
        
        # ETF returns
        hyg_ret_5d = (hyg_close.iloc[-1] / hyg_close.iloc[-5] - 1) * 100 if len(hyg_close) >= 5 else 0
        lqd_ret_5d = (lqd_close.iloc[-1] / lqd_close.iloc[-5] - 1) * 100 if len(lqd_close) >= 5 else 0
        
        relative_perf = hyg_ret_5d - lqd_ret_5d
        
        # Risk-off detection
        risk_off = hyg_ret_5d < -1 and lqd_ret_5d > hyg_ret_5d
        flight_to_quality = lqd_ret_5d > 0 and hyg_ret_5d < 0
        
        if risk_off:
            score -= 25
            details.append("RISK_OFF_SIGNAL")
        
        if flight_to_quality:
            score -= 15
            details.append("FLIGHT_TO_QUALITY")
        
        # Strategy
        if stress in ["CRISIS", "HIGH"]:
            strategy = "DEFENSIVE_CASH"
        elif stress == "ELEVATED":
            strategy = "REDUCE_RISK"
        elif stress == "LOW":
            strategy = "RISK_ON"
        else:
            strategy = "NORMAL"
        
        return CreditSignal(
            hyg_lqd_ratio=current_ratio,
            spread_direction=spread_dir,
            spread_percentile=percentile,
            credit_stress=stress,
            stress_score=stress_score,
            hyg_return_5d=hyg_ret_5d,
            lqd_return_5d=lqd_ret_5d,
            relative_performance=relative_perf,
            risk_off_signal=risk_off,
            flight_to_quality=flight_to_quality,
            credit_score=max(-100, min(100, score)),
            strategy=strategy,
            details=details
        )
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch data"""
        try:
            df = yf.download(symbol, period='60d', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return None
    
    def _default_result(self) -> CreditSignal:
        """Default result"""
        return CreditSignal(
            hyg_lqd_ratio=0.7, spread_direction="STABLE", spread_percentile=50,
            credit_stress="NORMAL", stress_score=35,
            hyg_return_5d=0, lqd_return_5d=0, relative_performance=0,
            risk_off_signal=False, flight_to_quality=False,
            credit_score=0, strategy="NORMAL", details=[]
        )


# Global
_analyzer = None

def get_credit_analyzer() -> CreditSpreadAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = CreditSpreadAnalyzer()
    return _analyzer


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing CreditSpreadAnalyzer...")
    
    analyzer = CreditSpreadAnalyzer()
    result = analyzer.analyze()
    
    print(f"\n{'='*60}")
    print("CREDIT SPREAD ANALYSIS")
    print('='*60)
    print(f"HYG/LQD Ratio: {result.hyg_lqd_ratio:.4f}")
    print(f"Spread: {result.spread_direction}")
    print(f"Percentile: {result.spread_percentile:.0f}%")
    print()
    print(f"Credit Stress: {result.credit_stress}")
    print(f"Stress Score: {result.stress_score:.0f}")
    print()
    print(f"HYG 5d: {result.hyg_return_5d:+.2f}%")
    print(f"LQD 5d: {result.lqd_return_5d:+.2f}%")
    print(f"Relative: {result.relative_performance:+.2f}%")
    print()
    print(f"Risk-Off: {result.risk_off_signal}")
    print(f"Flight to Quality: {result.flight_to_quality}")
    print(f"Strategy: {result.strategy}")
    print(f"Score: {result.credit_score:+d}")
    print(f"Details: {result.details}")
