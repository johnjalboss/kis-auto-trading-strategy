"""
2026 Cutting-Edge Quant Module 3: Cross-Asset Momentum Tracker (cross_asset_momentum.py)
==========================================================================================
Monitors intermarket capital rotation between Equities (SPY/QQQ), Bonds (TLT), Gold (GLD), and USD (UUP).
Provides macro conviction bonus when institutional capital rotates into Risk-On Equities.
"""

from typing import Dict, Any
from loguru import logger
import pandas as pd
from safe_math import safe_div


class CrossAssetMomentumTracker:
    """Intermarket Capital Rotation Scanner."""

    def analyze_cross_asset_flow(self, spy_df: pd.DataFrame, tlt_df: pd.DataFrame, gld_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculates 5-day relative momentum between Equities vs Safe Havens (Bonds & Gold).
        """
        try:
            if spy_df is None or tlt_df is None or gld_df is None:
                return {"regime": "NEUTRAL", "risk_on_score": 0, "conviction_bonus": 0}

            spy_ret = safe_div(spy_df['Close'].iloc[-1] - spy_df['Close'].iloc[-5], spy_df['Close'].iloc[-5], fallback=0.0)
            tlt_ret = safe_div(tlt_df['Close'].iloc[-1] - tlt_df['Close'].iloc[-5], tlt_df['Close'].iloc[-5], fallback=0.0)
            gld_ret = safe_div(gld_df['Close'].iloc[-1] - gld_df['Close'].iloc[-5], gld_df['Close'].iloc[-5], fallback=0.0)

            # Risk-On Differential = SPY Return - Average(TLT, GLD)
            safe_haven_ret = (tlt_ret + gld_ret) / 2.0
            risk_on_diff = spy_ret - safe_haven_ret

            if risk_on_diff > 0.015:
                regime = "STRONG_RISK_ON"
                conviction_bonus = +15
            elif risk_on_diff < -0.015:
                regime = "RISK_OFF_FLIGHT_TO_QUALITY"
                conviction_bonus = -15
            else:
                regime = "NEUTRAL"
                conviction_bonus = 0

            logger.info("🌐 [CROSS_ASSET] Regime: {} | SPY: {:.2f}% vs SafeHavens: {:.2f}% (Bonus: {} pts)",
                        regime, spy_ret * 100.0, safe_haven_ret * 100.0, conviction_bonus)

            return {
                "regime": regime,
                "risk_on_diff": risk_on_diff,
                "conviction_bonus": conviction_bonus
            }
        except Exception as e:
            logger.debug("CrossAssetMomentumTracker error: {}", e)
            return {"regime": "NEUTRAL", "risk_on_diff": 0.0, "conviction_bonus": 0}
