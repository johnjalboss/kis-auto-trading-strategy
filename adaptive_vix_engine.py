"""
Adaptive VIX Risk Engine (adaptive_vix_engine.py)
==================================================
Calculates dynamic 30-day Rolling VIX Percentile rank to adjust position risk exposure
and entry threshold dynamically based on relative market volatility.
"""

from typing import Dict, Any
import pandas as pd
from loguru import logger
from safe_math import safe_div


class AdaptiveVixEngine:
    def __init__(self, lookback_days: int = 30):
        self.lookback_days = lookback_days

    def evaluate_vix_regime(self, vix_df: pd.DataFrame, current_vix: float) -> Dict[str, Any]:
        """
        Calculates dynamic VIX rank & risk adjustment factor.
        """
        if vix_df is None or len(vix_df) < 10 or current_vix <= 0:
            return {"vix_rank_pct": 50.0, "risk_multiplier": 1.0, "score_bonus": 0, "regime": "NEUTRAL"}

        try:
            recent_vix = vix_df['Close'].tail(self.lookback_days)
            min_vix = float(recent_vix.min())
            max_vix = float(recent_vix.max())

            vix_range = max_vix - min_vix
            vix_rank_pct = safe_div((current_vix - min_vix) * 100.0, vix_range, fallback=50.0)

            if vix_rank_pct <= 20.0:
                # Dynamic Low Volatility -> Bullish confidence boost
                regime = "LOW_VOLATILITY_EXPANSION"
                risk_multiplier = 1.15
                score_bonus = +10
            elif vix_rank_pct >= 80.0:
                # Dynamic High Volatility Spike -> Capital protection
                regime = "HIGH_VOLATILITY_SPIKE"
                risk_multiplier = 0.65
                score_bonus = -15
            else:
                regime = "NORMAL_VOLATILITY"
                risk_multiplier = 1.0
                score_bonus = 0

            logger.info("📊 [ADAPTIVE_VIX] VIX: {:.2f} (Rank: {:.1f}%) -> Regime: {} | RiskMult: {:.2f}x",
                        current_vix, vix_rank_pct, regime, risk_multiplier)

            return {
                "vix_rank_pct": vix_rank_pct,
                "risk_multiplier": risk_multiplier,
                "score_bonus": score_bonus,
                "regime": regime
            }
        except Exception as e:
            logger.debug("AdaptiveVixEngine error: {}", e)
            return {"vix_rank_pct": 50.0, "risk_multiplier": 1.0, "score_bonus": 0, "regime": "NEUTRAL"}
