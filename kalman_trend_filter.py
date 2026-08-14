"""
3. 1D State-Space Kalman Filter Trend & Price Velocity Engine (kalman_trend_filter.py)
======================================================================================
Concept (Rudolf E. Kalman / Quantitative State-Space Modeling):
- Standard moving averages suffer from lag (phase delay).
- A 1D 2-State Kalman Filter models:
    x_t = [price_t, velocity_t]^T
    State Transition: x_t = F * x_{t-1} + w_t
    Measurement: z_t = H * x_t + v_t
- Dynamically estimates the true underlying price and instantaneous velocity (dv/dt).
- When Kalman Velocity is positive and accelerating (d2x/dt2 > 0), awards +20 points for zero-lag trend momentum!
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from loguru import logger

class KalmanTrendFilter:
    """Estimates zero-lag price state and trend velocity using a 2-State Kalman Filter"""

    def __init__(self, process_noise_var: float = 1e-4, measurement_noise_var: float = 1e-2):
        self.q = process_noise_var
        self.r = measurement_noise_var

    def analyze(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        res = {
            "symbol": symbol,
            "kalman_price": 0.0,
            "kalman_velocity": 0.0,
            "is_accelerating_trend": False,
            "score_bonus": 0,
            "label": "NORMAL_STATE"
        }

        if df is None or len(df) < 15 or 'Close' not in df.columns:
            return res

        try:
            prices = df['Close'].values
            n = len(prices)

            # State transition matrix F: [[1, dt], [0, 1]]
            dt = 1.0
            F = np.array([[1.0, dt], [0.0, 1.0]])
            H = np.array([[1.0, 0.0]])
            Q = np.array([[self.q * dt**3 / 3.0, self.q * dt**2 / 2.0],
                          [self.q * dt**2 / 2.0, self.q * dt]])
            R = np.array([[self.r]])

            # Initialize state estimate x and covariance P
            x = np.array([[prices[0]], [0.0]])
            P = np.eye(2) * 1.0

            filtered_prices = []
            filtered_velocities = []

            for z in prices:
                # 1. Predict
                x = F @ x
                P = F @ P @ F.T + Q

                # 2. Update
                y = z - (H @ x)[0, 0]  # measurement residual
                S = (H @ P @ H.T)[0, 0] + R[0, 0]
                K = (P @ H.T) / S  # Kalman gain

                x = x + K * y
                P = (np.eye(2) - K @ H) @ P

                filtered_prices.append(float(x[0, 0]))
                filtered_velocities.append(float(x[1, 0]))

            cur_k_price = filtered_prices[-1]
            cur_velocity = filtered_velocities[-1]
            prev_velocity = filtered_velocities[-2] if len(filtered_velocities) >= 2 else 0.0

            # Normalized velocity (% per day)
            norm_velocity = (cur_velocity / cur_k_price) * 100.0 if cur_k_price > 0 else 0.0
            acceleration = cur_velocity - prev_velocity

            res["kalman_price"] = round(cur_k_price, 2)
            res["kalman_velocity"] = round(norm_velocity, 3)

            # High-velocity accelerating trend: velocity > 0.3% / day and acceleration > 0
            if norm_velocity >= 0.40 and acceleration >= 0:
                res["is_accelerating_trend"] = True
                res["score_bonus"] = 20
                res["label"] = "KALMAN_VELOCITY_ACCELERATION"
                logger.info("🚀 [KALMAN_VELOCITY] {} zero-lag velocity +{:.2f}%/day (Accel={:+.3f}) -> +20 pts",
                            symbol, norm_velocity, acceleration)
            elif norm_velocity >= 0.15:
                res["score_bonus"] = 10
                res["label"] = "KALMAN_POSITIVE_VELOCITY"
            elif norm_velocity < -0.30:
                res["score_bonus"] = -15
                res["label"] = "KALMAN_DECELERATING_DOWNTREND"

            return res

        except Exception as e:
            logger.debug("Kalman filter analysis failed for {}: {}", symbol, e)
            return res
