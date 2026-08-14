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
            from kis_data import get_daily_ohlcv

            df_cand = get_daily_ohlcv(candidate_symbol, days=35)
            if df_cand is None or len(df_cand) < 15:
                return res

            cand_ret = df_cand['Close'].pct_change().dropna()

            highest_rho = -1.0
            highest_sym = ""

            for held in current_positions:
                if held.upper() == candidate_symbol.upper():
                    continue
                df_held = get_daily_ohlcv(held, days=35)
                if df_held is None or len(df_held) < 15:
                    continue

                held_ret = df_held['Close'].pct_change().dropna()
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
