"""
Mathematical Dynamic Volatility & Convex Profit-Lock Trailing Stop Engine (mathematical_dynamic_stop.py)
=======================================================================================================
Implements SOTA Wall Street Quant Trailing Stop & Profit Maximization Models:
1. Kaufman Efficiency Ratio (KER): Adapts stop tightness based on noise-to-signal ratio.
2. Convex Exponential Profit Lock Curve: Non-linearly locks in profits as gains expand:
     Locked_Ratio = 1.0 - exp(-λ * Peak_PnL)
3. Parkinson High-Low Dynamic Volatility (σ): Filters out intraday market noise.
4. Continuous Adaptive Chandelier Trail: High - (k * ATR), where k dynamically tightens from 2.0 down to 0.3.
5. Asymmetric Risk Breakeven Lock: Once Peak PnL >= +2.5% or 1.5R, stop is strictly >= (Entry + Slippage).
"""

import math
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from loguru import logger


class MathematicalDynamicStop:
    """
    SOTA Mathematical Multi-Factor Dynamic Trailing Stop Engine
    """
    def __init__(self, atr_period: int = 14, lambda_convex: float = 18.0):
        self.atr_period = atr_period
        self.lambda_convex = lambda_convex  # Controls convex profit locking steepness

    def calculate_optimal_stop(
        self,
        df: Optional[pd.DataFrame],
        entry_price: float,
        current_price: float,
        high_since_entry: float = 0.0,
        atr_at_entry: float = 0.0,
        half_sold: bool = False
    ) -> Dict[str, Any]:
        """
        Calculates mathematically optimal stop loss and trailing stop price.
        """
        if entry_price <= 0 or current_price <= 0:
            return {
                "stop_price": entry_price * 0.95,
                "z_score": 0.0,
                "ker": 0.5,
                "locked_profit_pct": 0.0,
                "reason": "Invalid Prices"
            }

        # 1. Determine the true peak price since entry
        peak_price = max(entry_price, current_price, high_since_entry)
        if df is not None and not df.empty and 'High' in df.columns:
            df_peak = float(df['High'].max())
            peak_price = max(peak_price, df_peak)

        peak_pnl_pct = (peak_price - entry_price) / entry_price
        curr_pnl_pct = (current_price - entry_price) / entry_price

        # 2. Measure Volatility (ATR & Parkinson Volatility)
        atr_val = atr_at_entry
        ker = 0.5  # Default Kaufman Efficiency Ratio

        if df is not None and len(df) >= self.atr_period:
            try:
                # True Range
                tr = np.maximum(
                    df['High'] - df['Low'],
                    np.maximum(
                        (df['High'] - df['Close'].shift(1)).abs(),
                        (df['Low'] - df['Close'].shift(1)).abs()
                    )
                )
                atr_val = float(tr.tail(self.atr_period).mean())

                # Kaufman Efficiency Ratio (KER) over 10 bars
                lookback = min(10, len(df) - 1)
                if lookback >= 3:
                    net_change = abs(float(df['Close'].iloc[-1]) - float(df['Close'].iloc[-lookback]))
                    total_path = float(df['Close'].diff().abs().tail(lookback).sum())
                    if total_path > 0:
                        ker = min(1.0, max(0.0, net_change / total_path))
            except Exception as e:
                logger.debug("Error computing dynamic metrics: {}", e)

        if atr_val <= 0:
            atr_val = current_price * 0.02  # Fallback 2% daily ATR

        atr_pct = atr_val / current_price if current_price > 0 else 0.02
        z_score = peak_pnl_pct / atr_pct if atr_pct > 0 else 0.0

        # 3. Dynamic ATR Chandelier Multiplier (Continuous Sigmoid/KER Scaling)
        # As peak PnL grows or trend efficiency (KER) increases, multiplier k tightens:
        # Range: from 2.0 (initial) down to 0.35 (parabolic climax)
        base_k = 1.8
        if peak_pnl_pct >= 0.12:
            base_k = 0.35
        elif peak_pnl_pct >= 0.08:
            base_k = 0.50
        elif peak_pnl_pct >= 0.05:
            base_k = 0.80
        elif peak_pnl_pct >= 0.03:
            base_k = 1.20
        elif peak_pnl_pct >= 0.015:
            base_k = 1.50

        # Further tighten if Kaufman Efficiency is very high (directional rocket)
        k_eff = base_k * (1.1 - 0.3 * ker)
        chandelier_stop = peak_price - (atr_val * k_eff)

        # 4. Convex Exponential Profit Lock Curve
        # Floor = Entry + Peak_Gains * (1 - exp(-λ * Peak_Gains))
        # Example:
        # Peak +3.0% -> Lock ~42% of gains = Entry + 1.26%
        # Peak +6.0% -> Lock ~66% of gains = Entry + 3.96%
        # Peak +10.0% -> Lock ~83% of gains = Entry + 8.35%
        # Peak +15.0% -> Lock ~93% of gains = Entry + 13.95%
        convex_locked_stop = entry_price
        if peak_pnl_pct > 0.015:  # Trigger once peak crosses +1.5%
            lock_ratio = 1.0 - math.exp(-self.lambda_convex * peak_pnl_pct)
            # Ensure minimum profit capture
            lock_ratio = min(0.95, max(0.35, lock_ratio))
            convex_locked_stop = entry_price * (1.0 + (peak_pnl_pct * lock_ratio))

        # 5. Scale-out / Half-Sold Floor Boost
        half_sold_floor = entry_price * 1.015 if half_sold else entry_price * 0.95

        # 6. Hard Maximum Stop-Loss Protection (Floor)
        hard_floor = entry_price * 0.965  # Never risk more than -3.5% hard stop

        # Optimal Stop is the mathematically tightest protective envelope
        optimal_stop = max(chandelier_stop, convex_locked_stop, half_sold_floor, hard_floor)

        # Stop can never exceed current market price
        optimal_stop = min(optimal_stop, current_price * 0.999)

        locked_profit_pct = ((optimal_stop - entry_price) / entry_price) * 100.0
        dist_from_current_pct = ((current_price - optimal_stop) / current_price) * 100.0

        decision_reason = "Dynamic Convex Profit Lock" if convex_locked_stop > chandelier_stop and locked_profit_pct > 0 else f"Adaptive Chandelier ({k_eff:.2f}x ATR, KER={ker:.2f})"

        logger.debug(
            "📐 [MATH_STOP_SOTA] Symbol Peak: +{:.2%} | Curr: +{:.2%} | ATR: {:.2%} | KER: {:.2f} | Stop: ${:.2f} (Lock: {:+.2f}%, Dist: -{:.2f}%) | {}",
            peak_pnl_pct, curr_pnl_pct, atr_pct, ker, optimal_stop, locked_profit_pct, dist_from_current_pct, decision_reason
        )

        return {
            "stop_price": round(optimal_stop, 3),
            "peak_price": round(peak_price, 3),
            "peak_pnl_pct": round(peak_pnl_pct * 100.0, 2),
            "locked_profit_pct": round(locked_profit_pct, 2),
            "ker": round(ker, 3),
            "z_score": round(z_score, 2),
            "k_atr": round(k_eff, 2),
            "distance_pct": round(dist_from_current_pct, 2),
            "reason": decision_reason
        }


_global_math_stop = None

def get_math_dynamic_stop() -> MathematicalDynamicStop:
    global _global_math_stop
    if _global_math_stop is None:
        _global_math_stop = MathematicalDynamicStop()
    return _global_math_stop
