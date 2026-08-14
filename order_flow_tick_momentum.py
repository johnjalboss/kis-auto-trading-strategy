"""
2. Smart Money Tick Flow Momentum Engine (order_flow_tick_momentum.py)
=====================================================================
Detects institutional market order aggression using Bar Microstructure Flow:
- Approximates buyer-initiated volume vs seller-initiated volume using Candle Range & Close Position.
- Lee-Ready (1991) / Bulk Volume Classification (BVC):
  Buyer Volume Fraction = 0.5 + (Close - (High + Low)/2) / (High - Low)
- Computes 5-day Rolling Aggressive Buyer Volume Intensity ($I_{\text{flow}}$).
- Rewards stocks with strong buyer pressure (>65% buyer volume) with +15 points.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any
from loguru import logger

class OrderFlowTickMomentumEngine:
    """Measures Smart Money Order Flow & Aggressive Buyer Intensity"""

    def analyze(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        res = {
            "symbol": symbol,
            "buyer_flow_pct": 50.0,
            "flow_intensity_zscore": 0.0,
            "is_aggressive_accumulation": False,
            "score_bonus": 0,
            "label": "BALANCED_FLOW"
        }

        if df is None or len(df) < 10 or 'Volume' not in df.columns:
            return res

        try:
            high = df['High'].values
            low = df['Low'].values
            close = df['Close'].values
            vol = df['Volume'].values

            rng = high - low
            rng = np.where(rng <= 1e-6, 1e-6, rng)

            # Bulk Volume Classification (BVC): estimate buyer volume fraction
            # Close near High -> Buyer Fraction close to 1.0; Close near Low -> Buyer Fraction close to 0.0
            mid = (high + low) / 2.0
            fraction = 0.5 + ((close - mid) / rng) * 0.5
            fraction = np.clip(fraction, 0.05, 0.95)

            buyer_vol = vol * fraction
            seller_vol = vol * (1.0 - fraction)

            recent_buyer = np.sum(buyer_vol[-5:])
            recent_total = np.sum(vol[-5:])

            if recent_total > 0:
                buyer_pct = (recent_buyer / recent_total) * 100.0
            else:
                buyer_pct = 50.0

            res["buyer_flow_pct"] = round(float(buyer_pct), 1)

            # Compute flow intensity z-score vs 20-day mean
            if len(df) >= 20:
                daily_buyer_pct = (buyer_vol / np.where(vol <= 0, 1.0, vol)) * 100.0
                mean_20 = np.mean(daily_buyer_pct[-20:])
                std_20 = np.std(daily_buyer_pct[-20:])
                if std_20 > 1e-4:
                    z = (buyer_pct - mean_20) / std_20
                    res["flow_intensity_zscore"] = round(float(z), 2)

            if buyer_pct >= 65.0:
                res["is_aggressive_accumulation"] = True
                res["score_bonus"] = 15
                res["label"] = "AGGRESSIVE_BUYER_FLOW"
            elif buyer_pct >= 55.0:
                res["score_bonus"] = 5
                res["label"] = "MODERATE_BUYER_FLOW"
            elif buyer_pct <= 35.0:
                res["score_bonus"] = -10
                res["label"] = "SELLER_DOMINATED_DISTRIBUTION"

            return res

        except Exception as e:
            logger.debug("Order flow tick momentum failed for {}: {}", symbol, e)
            return res
