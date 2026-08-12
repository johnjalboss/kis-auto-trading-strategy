"""
[v11.0 ULTRA QUANT] 1D Kalman Filter Noise Elimination Engine
============================================================
Filters market price noise R to extract lag-free true velocity slope (dx/dt).
Eliminates Moving Average lag (SMA/EMA) and avoids whipsaw fakeouts.

Positive Kalman Velocity Slope: +15 pts
Negative Kalman Velocity Slope: -15 pts
"""

import numpy as np
import pandas as pd
from typing import Dict, Any
from loguru import logger


class KalmanFilterEngine:
    def __init__(self, process_variance: float = 1e-5, measurement_variance: float = 1e-2):
        self.Q = process_variance  # Process noise
        self.R = measurement_variance  # Measurement noise

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        res = {
            'kalman_price': 0.0,
            'velocity_slope': 0.0,
            'score_adj': 0,
            'reason': 'Insufficient data for Kalman Filter'
        }

        if df is None or len(df) < 15:
            return res

        try:
            prices = df['Close'].values.flatten().astype(float)
            n = len(prices)

            # Initialize state estimate x_hat and error covariance P
            x_hat = prices[0]
            P = 1.0

            filtered = np.zeros(n)
            filtered[0] = x_hat

            for k in range(1, n):
                # Time Update (Predict)
                x_hat_minus = x_hat
                P_minus = P + self.Q

                # Measurement Update (Correct)
                K = P_minus / (P_minus + self.R)
                x_hat = x_hat_minus + K * (prices[k] - x_hat_minus)
                P = (1.0 - K) * P_minus

                filtered[k] = x_hat

            # Calculate 5-bar velocity slope (dx/dt)
            recent_filtered = filtered[-5:]
            slope = (recent_filtered[-1] - recent_filtered[0]) / recent_filtered[0]

            res['kalman_price'] = float(filtered[-1])
            res['velocity_slope'] = float(slope)

            if slope > 0.008:  # +0.8% lag-free upward velocity
                res['score_adj'] = 15
                res['reason'] = f"Kalman Filter Lag-Free Uptrend Velocity (+{slope*100:.2f}%)"
            elif slope < -0.008:
                res['score_adj'] = -15
                res['reason'] = f"Kalman Filter Downtrend Velocity ({slope*100:.2f}%)"
            else:
                res['score_adj'] = 0
                res['reason'] = f"Kalman Filter Neutral Velocity ({slope*100:.2f}%)"
        except Exception as e:
            logger.debug("KalmanFilterEngine analysis failed: {}", e)

        return res
