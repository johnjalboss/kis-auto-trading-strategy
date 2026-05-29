"""
Correlation Regime Detector
==============================
Detect when correlations break down.
"""

from dataclasses import dataclass
from typing import Dict, List
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class CorrelationRegime:
    regime: str  # "HIGH_CORR", "NORMAL", "DECORRELATED"
    avg_correlation: float
    
    # Key pairs
    spy_qqq: float  # S&P vs Nasdaq
    spy_gold: float  # S&P vs Gold
    spy_bonds: float  # S&P vs Bonds
    
    # Implications
    diversification_benefit: str
    risk_level: str
    recommendation: str


class CorrelationRegimeDetector:
    """
    Correlation Regime Analysis
    
    Regimes:
    1. HIGH_CORR: Everything moves together (crisis)
    2. NORMAL: Normal diversification works
    3. DECORRELATED: Unusual, check for opportunities
    
    When correlations spike to 1:
    - Hedges don't work
    - Need to reduce overall exposure
    """
    
    PAIRS = [
        ('SPY', 'QQQ'),
        ('SPY', 'GLD'),
        ('SPY', 'TLT'),
    ]
    
    def __init__(self):
        pass
    
    def analyze(self, lookback: int = 30) -> CorrelationRegime:
        """Analyze current correlation regime"""
        
        try:
            # Download data
            symbols = ['SPY', 'QQQ', 'GLD', 'TLT']
            raw_data = yf.download(symbols, period='3mo', progress=False)
            
            if raw_data.empty:
                return self._default()
            
            # yfinance MultiIndex 복원 및 평탄화
            # (Price, Ticker) MultiIndex 구조인 경우 'Close' 컬럼만 추출
            if isinstance(raw_data.columns, pd.MultiIndex):
                if 'Close' in raw_data.columns.levels[0]:
                    data = raw_data['Close']
                else:
                    # 'Close' 레벨이 없을 경우 차선책으로 Close가 포함된 컬럼 필터링
                    close_cols = [col for col in raw_data.columns if col[0] == 'Close']
                    if close_cols:
                        data = raw_data[close_cols]
                        # 컬럼명을 Ticker 이름으로만 변경
                        data.columns = [col[1] for col in data.columns]
                    else:
                        data = raw_data
            else:
                # 단일 인덱스인 경우
                if 'Close' in raw_data.columns:
                    data = raw_data[['Close']]
                else:
                    data = raw_data
            
            # DataFrame이 맞는지 재확인하고, 종목 컬럼만 남김
            if isinstance(data, pd.Series):
                data = data.to_frame()
                
            if data.empty:
                return self._default()
            
            # Calculate returns
            returns = data.pct_change().dropna()
            if returns.empty:
                return self._default()
            
            # Recent correlations
            recent = returns.tail(lookback)
            corr_matrix = recent.corr()
            
            # 존재 여부 확인 후 안전하게 스칼라 float로 추출 함수 정의
            def safe_get_corr(matrix: pd.DataFrame, s1: str, s2: str, default_val: float) -> float:
                try:
                    if s1 in matrix.index and s2 in matrix.columns:
                        val = matrix.loc[s1, s2]
                        # 만약 결과가 Series 나 DataFrame 형태라면 첫 번째 요소 추출
                        if isinstance(val, (pd.Series, pd.DataFrame)):
                            val = val.iloc[0] if isinstance(val, pd.Series) else val.iloc[0, 0]
                        return float(val)
                except Exception as ex:
                    logger.debug(f"Failed to extract correlation for {s1}-{s2}: {ex}")
                return default_val
            
            spy_qqq = safe_get_corr(corr_matrix, 'SPY', 'QQQ', 0.9)
            spy_gold = safe_get_corr(corr_matrix, 'SPY', 'GLD', -0.2)
            spy_bonds = safe_get_corr(corr_matrix, 'SPY', 'TLT', -0.3)
            
            # Average correlation (excluding diagonal)
            try:
                mask = ~np.eye(corr_matrix.shape[0], dtype=bool)
                avg_corr_val = corr_matrix.where(mask).mean().mean()
                if isinstance(avg_corr_val, (pd.Series, pd.DataFrame)):
                    avg_corr = float(avg_corr_val.iloc[0] if isinstance(avg_corr_val, pd.Series) else avg_corr_val.iloc[0, 0])
                else:
                    avg_corr = float(avg_corr_val)
            except Exception:
                avg_corr = 0.5
            
            # Determine regime (모든 비교 대상이 확실한 float 스칼라임)
            if avg_corr > 0.7 or spy_qqq > 0.95:
                regime = "HIGH_CORR"
                diversification = "LOW - hedges not working"
                risk = "HIGH"
                rec = "REDUCE EXPOSURE: High correlation, diversification not working"
            elif spy_gold > 0.3 or spy_bonds > 0.3:
                regime = "RISK_ON"
                diversification = "MODERATE"
                risk = "ELEVATED"
                rec = "CAUTION: Traditional hedges not protecting"
            elif spy_gold < -0.3 and spy_bonds < -0.3:
                regime = "NORMAL"
                diversification = "HIGH - hedges working"
                risk = "NORMAL"
                rec = "Normal regime, diversification effective"
            else:
                regime = "DECORRELATED"
                diversification = "VARIABLE"
                risk = "MONITOR"
                rec = "Unusual correlations, monitor closely"
            
            return CorrelationRegime(
                regime=regime,
                avg_correlation=avg_corr,
                spy_qqq=spy_qqq,
                spy_gold=spy_gold,
                spy_bonds=spy_bonds,
                diversification_benefit=diversification,
                risk_level=risk,
                recommendation=rec
            )
            
        except Exception as e:
            import traceback
            logger.debug(f"Correlation analysis error: {e}\n{traceback.format_exc()}")
            return self._default()
    
    def _default(self) -> CorrelationRegime:
        return CorrelationRegime("UNKNOWN", 0.5, 0.9, -0.2, -0.3, "UNKNOWN", "UNKNOWN", "No data")


def get_correlation_regime() -> CorrelationRegimeDetector:
    return CorrelationRegimeDetector()


if __name__ == "__main__":
    print("Testing CorrelationRegimeDetector (Robust Edition)...")
    cr = CorrelationRegimeDetector()
    
    regime = cr.analyze()
    
    print(f"\n{'='*50}")
    print("CORRELATION REGIME")
    print('='*50)
    print(f"Regime: {regime.regime}")
    print(f"Avg Correlation: {regime.avg_correlation:.2f}")
    print()
    print(f"SPY-QQQ: {regime.spy_qqq:.2f}")
    print(f"SPY-Gold: {regime.spy_gold:.2f}")
    print(f"SPY-Bonds: {regime.spy_bonds:.2f}")
    print()
    print(f"Diversification: {regime.diversification_benefit}")
    print(f"Risk Level: {regime.risk_level}")
    print(f"Recommendation: {regime.recommendation}")
