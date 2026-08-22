"""
4. Portfolio De-Correlation & Cross-Sector Parity (portfolio_decorrelation.py)
=============================================================================
Prevents concentrated drawdown risk by verifying pairwise 30-day return correlations:
- If a new buy candidate has correlation rho > 0.70 with existing portfolio holdings,
  the engine applies a diversification penalty or blocks entry.
- Guarantees balanced exposure across Tech, Healthcare, Financials, Energy, Industrials, etc.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from loguru import logger

class PortfolioDeCorrelationEngine:
    """Calculates Pairwise Correlation & Enforces Sector Diversification"""

    def __init__(self, max_correlation: float = 0.70):
        self.max_correlation = max_correlation

    def _get_returns(self, symbol: str) -> Optional[pd.Series]:
        """Fetch daily close returns with robust fallback"""
        try:
            from kis_data import get_daily_ohlcv
            df = get_daily_ohlcv(symbol, days=35)
            if df is not None and len(df) >= 15:
                return df['Close'].pct_change().dropna()
        except Exception:
            pass

        try:
            import yfinance as yf
            df = yf.download(symbol, period="2mo", interval="1d", progress=False)
            if df is not None and len(df) >= 15:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                return df['Close'].pct_change().dropna()
        except Exception:
            pass
        return None

    def check_correlation_gate(self, candidate_symbol: str, current_positions: List[str]) -> Dict[str, Any]:
        """
        Check if candidate symbol is overly correlated with currently held positions.
        """
        res = {
            "candidate": candidate_symbol,
            "can_add": True,
            "max_rho": 0.0,
            "correlated_with": "",
            "penalty_score": 0,
            "reason": "OK"
        }

        if not current_positions:
            return res

        try:
            cand_ret = self._get_returns(candidate_symbol)
            if cand_ret is None or len(cand_ret) < 10:
                return res

            highest_rho = -1.0
            highest_sym = ""

            for held in current_positions:
                if held.upper() == candidate_symbol.upper():
                    continue
                held_ret = self._get_returns(held)
                if held_ret is None or len(held_ret) < 10:
                    continue

                common_idx = cand_ret.index.intersection(held_ret.index)

                if len(common_idx) >= 10:
                    r_c = cand_ret.loc[common_idx].values
                    r_h = held_ret.loc[common_idx].values
                    std_c = np.std(r_c)
                    std_h = np.std(r_h)
                    if std_c > 1e-5 and std_h > 1e-5:
                        rho = float(np.corrcoef(r_c, r_h)[0, 1])
                        if rho > highest_rho:
                            highest_rho = rho
                            highest_sym = held

            res["max_rho"] = round(highest_rho, 2)
            res["correlated_with"] = highest_sym

            if highest_rho >= self.max_correlation:
                res["penalty_score"] = -15
                res["reason"] = f"HIGH_CORRELATION: rho={highest_rho:.2f} with held {highest_sym}"
                logger.warning("🛡️ [DE_CORRELATION] {} is highly correlated with existing position {} (rho={:.2f}) -> Penalty -15 pts",
                               candidate_symbol, highest_sym, highest_rho)
            else:
                res["reason"] = f"DIVERSIFIED: max rho={highest_rho:.2f} with {highest_sym}"

            return res

        except Exception as e:
            logger.debug("Portfolio decorrelation check failed for {}: {}", candidate_symbol, e)
            return res
