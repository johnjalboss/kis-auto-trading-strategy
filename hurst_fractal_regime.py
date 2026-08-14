"""
Hurst Exponent Fractal Regime Filter (hurst_fractal_regime.py)
==============================================================
Applies Mandelbrot's Fractal Market Hypothesis (FMH) & Rescaled Range (R/S)
analysis on price time-series to classify market dynamics:
- H >= 0.58 : PERSISTENT_TREND (True momentum, high breakout conviction)
- 0.45 <= H < 0.58 : RANDOM_WALK_NOISE (Chop/whipsaw risk, suppress false breakouts)
- H < 0.45 : MEAN_REVERTING (Anticipate mean-reversion pullbacks)
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
from loguru import logger


class HurstFractalRegimeFilter:
    """Calculates Hurst Exponent and classifies fractal regime of price action."""

    @staticmethod
    def calculate_hurst(prices: pd.Series, max_lags: int = 20) -> float:
        """
        Calculates Hurst Exponent using Rescaled Range (R/S) methodology.
        H = log(R/S) / log(N)
        """
        try:
            if prices is None or len(prices) < 25:
                return 0.50

            ts = np.array(prices.dropna().values, dtype=float)
            if len(ts) < 25:
                return 0.50

            # Log returns
            log_returns = np.diff(np.log(ts))
            n = len(log_returns)
            if n < 20:
                return 0.50

            lags = []
            rs_values = []

            for lag in range(5, min(max_lags, n // 2) + 1):
                # Subdivide series into chunks of size 'lag'
                num_chunks = n // lag
                if num_chunks < 1:
                    continue

                chunk_rs = []
                for i in range(num_chunks):
                    chunk = log_returns[i * lag : (i + 1) * lag]
                    mean = np.mean(chunk)
                    # Mean-adjusted cumulative deviations
                    cum_dev = np.cumsum(chunk - mean)
                    r = np.max(cum_dev) - np.min(cum_dev)
                    s = np.std(chunk, ddof=1)
                    if s > 1e-8:
                        chunk_rs.append(r / s)

                if chunk_rs:
                    lags.append(lag)
                    rs_values.append(np.mean(chunk_rs))

            if len(lags) < 3 or len(rs_values) < 3:
                return 0.50

            # Linear regression of log(R/S) vs log(lag)
            log_lags = np.log(lags)
            log_rs = np.log(rs_values)
            poly = np.polyfit(log_lags, log_rs, 1)
            hurst = float(poly[0])

            # Bound Hurst between 0.0 and 1.0
            return max(0.05, min(0.95, hurst))
        except Exception as e:
            logger.debug("Hurst calculation fallback: {}", e)
            return 0.50

    def analyze(self, df: Optional[pd.DataFrame], symbol: str = "") -> Dict[str, Any]:
        """
        Analyzes price series and returns fractal regime classification.
        """
        default_res = {
            "symbol": symbol,
            "hurst_exponent": 0.50,
            "regime": "RANDOM_WALK_NOISE",
            "is_persistent_trend": False,
            "is_random_walk": True,
            "is_mean_reverting": False,
            "score_bonus": 0,
            "allow_breakout": True,
            "confidence": 50.0
        }

        if df is None or len(df) < 25:
            return default_res

        try:
            close_series = df['Close'] if 'Close' in df else df.iloc[:, 0]
            # Use rolling 50-day window
            eval_window = close_series.iloc[-50:] if len(close_series) >= 50 else close_series
            hurst = self.calculate_hurst(eval_window)

            if hurst >= 0.58:
                regime = "PERSISTENT_TREND"
                is_persistent = True
                is_random = False
                is_mean_rev = False
                score_bonus = 20 if hurst >= 0.65 else 12
                allow_breakout = True
                confidence = min(95.0, 50.0 + (hurst - 0.50) * 100.0)
            elif hurst < 0.45:
                regime = "MEAN_REVERTING"
                is_persistent = False
                is_random = False
                is_mean_rev = True
                score_bonus = -10  # Suppress breakout chasing
                allow_breakout = False
                confidence = min(95.0, 50.0 + (0.50 - hurst) * 100.0)
            else:
                regime = "RANDOM_WALK_NOISE"
                is_persistent = False
                is_random = True
                is_mean_rev = False
                score_bonus = -5  # Slight penalty for noise
                allow_breakout = True
                confidence = 50.0

            return {
                "symbol": symbol,
                "hurst_exponent": round(hurst, 3),
                "regime": regime,
                "is_persistent_trend": is_persistent,
                "is_random_walk": is_random,
                "is_mean_reverting": is_mean_rev,
                "score_bonus": score_bonus,
                "allow_breakout": allow_breakout,
                "confidence": round(confidence, 1)
            }
        except Exception as e:
            logger.debug("HurstFractalRegimeFilter analyze failed for {}: {}", symbol, e)
            return default_res
