"""
Mathematical Dynamic Volatility Z-Score Stop Engine (mathematical_dynamic_stop.py)
===================================================================================
Calculates dynamic, mathematically optimized stop lines using Volatility-Normalized Z-Scores:
  Daily Volatility σ = ATR(14) / Current_Price
  Z-Score = Peak_PnL_Pct / σ
  Dynamic Locked Profit Floor = Entry_Price * (1 + max(0, (Z - 1.0) * σ))

Replaces fixed percentage thresholds with continuous statistical deviation modeling.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
from loguru import logger

class MathematicalDynamicStop:
    def __init__(self, atr_period: int = 14, z_safety_margin: float = 1.0):
        self.atr_period = atr_period
        self.z_safety_margin = z_safety_margin

    def calculate_optimal_stop(self, df: pd.DataFrame, entry_price: float, current_price: float) -> Dict[str, Any]:
        if df is None or len(df) < self.atr_period or entry_price <= 0 or current_price <= 0:
            return {"stop_price": entry_price * 0.94, "z_score": 0.0, "sigma_pct": 2.0, "reason": "Insufficient Data"}

        # 1. Calculate 14-day ATR and Volatility Coefficient σ (Sigma)
        df = df.copy()
        df['TR'] = np.maximum(
            df['High'] - df['Low'],
            np.maximum((df['High'] - df['Close'].shift(1)).abs(), (df['Low'] - df['Close'].shift(1)).abs())
        )
        atr_val = float(df['TR'].tail(self.atr_period).mean())
        highest_peak = max(float(df['High'].max()), current_price)

        sigma_pct = (atr_val / current_price) if current_price > 0 else 0.02 # e.g. 0.012 for 1.2% daily vol
        pnl_pct = (current_price - entry_price) / entry_price
        peak_pnl_pct = (highest_peak - entry_price) / entry_price

        # 2. Compute Statistical Z-Score of the Peak Move
        z_score = peak_pnl_pct / sigma_pct if sigma_pct > 0 else 0.0

        # 3. Calculate Chandelier ATR Exit Base
        chandelier_stop = highest_peak - (2.0 * atr_val)

        # 4. Compute Volatility-Normalized Z-Score Profit Lock Floor
        # If Peak move >= 2.0σ, lock in (Z - z_safety_margin)*σ profit
        locked_stop = entry_price
        if z_score >= 2.0:
            locked_profit_ratio = (z_score - self.z_safety_margin) * sigma_pct
            locked_stop = entry_price * (1.0 + locked_profit_ratio)

        # Optimal Stop Price is the highest of Chandelier Stop or Z-Score Locked Floor
        optimal_stop = max(chandelier_stop, locked_stop, entry_price * 0.94)
        dist_pct = ((current_price - optimal_stop) / current_price) * 100.0 if current_price > 0 else 0.0

        logger.debug("📐 [MATH_STOP] Entry: ${:.2f} | Curr: ${:.2f} | σ={:.2%} | Z={:.2f}σ | Math Stop: ${:.2f} (Dist: -{:.1f}%)",
                     entry_price, current_price, sigma_pct * 100, z_score, optimal_stop, dist_pct)

        return {
            "stop_price": optimal_stop,
            "z_score": z_score,
            "sigma_pct": sigma_pct * 100,
            "highest_peak": highest_peak,
            "atr": atr_val,
            "reason": f"Z-Score ({z_score:.2f}σ) Vol-Normalized Floor" if z_score >= 2.0 else "Chandelier ATR Trailing"
        }

def get_math_dynamic_stop() -> MathematicalDynamicStop:
    return MathematicalDynamicStop()
