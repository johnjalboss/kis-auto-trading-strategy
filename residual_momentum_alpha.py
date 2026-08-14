"""
1. Residual Momentum Pure Alpha Engine (residual_momentum_alpha.py)
====================================================================
Academic Foundation:
- Blitz, Huij, & Martens (2011) "Residual Momentum" (Journal of Empirical Finance)
- Removes market beta (SPY) exposure to isolate pure idiosyncratic stock alpha (epsilon_i).
- Standardizes residual returns by residual volatility: Z_eps = cumsum(eps) / sigma(eps).

Benefits:
- Prevents buying fake momentum stocks that only rose because the broad market rallied.
- Detects true institutional alpha stocks that show persistent idiosyncratic outperformance.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from loguru import logger

class ResidualMomentumAlpha:
    """Calculates Beta-adjusted Residual Momentum Alpha (Blitz et al. 2011)"""

    def __init__(self, window: int = 60):
        self.window = window
        self._spy_cache = None
        self._spy_cache_time = 0

    def _get_spy_returns(self) -> Optional[pd.Series]:
        """Fetch SPY benchmark daily returns"""
        try:
            import time
            from kis_data import get_daily_ohlcv
            now = time.time()
            if self._spy_cache is not None and (now - self._spy_cache_time < 3600):
                return self._spy_cache

            df_spy = get_daily_ohlcv("SPY", days=self.window + 20)
            if df_spy is not None and len(df_spy) >= 20:
                ret = df_spy['Close'].pct_change().dropna()
                self._spy_cache = ret
                self._spy_cache_time = now
                return ret
        except Exception as e:
            logger.debug("Failed to fetch SPY returns for ResidualMomentum: {}", e)
        return None

    def analyze(self, df_stock: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        Analyze stock DataFrame and compute Residual Momentum Z-Score
        """
        res = {
            "symbol": symbol,
            "beta": 1.0,
            "residual_zscore": 0.0,
            "is_pure_alpha": False,
            "score_bonus": 0,
            "label": "NEUTRAL_RESIDUAL"
        }

        if df_stock is None or len(df_stock) < 30:
            return res

        try:
            spy_ret = self._get_spy_returns()
            stock_ret = df_stock['Close'].pct_change().dropna()

            if spy_ret is None or len(spy_ret) < 20 or len(stock_ret) < 20:
                # Simple fallback: 20-day return vs volatility
                vol = stock_ret.std()
                if vol > 0:
                    z = (stock_ret.mean() / vol) * np.sqrt(20)
                    res["residual_zscore"] = round(float(z), 2)
                return res

            # Align series
            common_idx = stock_ret.index.intersection(spy_ret.index)
            if len(common_idx) < 20:
                # Use positional alignment if index mismatch
                min_len = min(len(stock_ret), len(spy_ret), self.window)
                y = stock_ret.values[-min_len:]
                x = spy_ret.values[-min_len:]
            else:
                y = stock_ret.loc[common_idx].values[-self.window:]
                x = spy_ret.loc[common_idx].values[-self.window:]

            if len(y) < 15 or len(x) < 15:
                return res

            # Linear regression: y = alpha + beta * x + eps
            var_x = np.var(x)
            if var_x < 1e-8:
                beta = 1.0
                alpha = np.mean(y) - beta * np.mean(x)
            else:
                cov_xy = np.cov(x, y)[0, 1]
                beta = cov_xy / var_x
                alpha = np.mean(y) - beta * np.mean(x)

            # Residuals: eps = y - (alpha + beta * x)
            residuals = y - (alpha + beta * x)
            res_std = np.std(residuals)

            if res_std > 1e-6:
                # Standardized 20-day residual cumulative return
                z_score = float(np.sum(residuals[-20:]) / (res_std * np.sqrt(20)))
            else:
                z_score = 0.0

            res["beta"] = round(float(beta), 2)
            res["residual_zscore"] = round(float(z_score), 2)

            if z_score >= 1.5:
                res["is_pure_alpha"] = True
                res["score_bonus"] = 20
                res["label"] = "HIGH_PURE_ALPHA"
            elif z_score >= 0.75:
                res["score_bonus"] = 10
                res["label"] = "MODERATE_ALPHA"
            elif z_score < -1.0:
                res["score_bonus"] = -10
                res["label"] = "NEGATIVE_RESIDUAL_LAGGARD"

            return res

        except Exception as e:
            logger.debug("Residual momentum analysis failed for {}: {}", symbol, e)
            return res
