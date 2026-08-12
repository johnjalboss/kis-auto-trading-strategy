"""
2026 Cutting-Edge Quant Module 1: Gamma Squeeze Radar (gamma_squeeze_radar.py)
=================================================================================
Tracks Option Market Maker Dealer Gamma Exposure (GEX) & Call/Put Wall levels.
Identifies Gamma Flip Points where forced dealer delta hedging accelerates parabolic squeeze breakouts.
"""

from typing import Dict, Any
from loguru import logger
from safe_math import safe_div


class GammaSqueezeRadar:
    """Dealer Gamma Exposure (GEX) & Option Squeeze Analyzer."""

    def analyze_gamma(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """
        Evaluates options GEX flow & gamma squeeze potential for symbol.
        """
        if current_price <= 0:
            return {"score_bonus": 0, "is_gamma_squeeze": False, "reason": "Invalid price"}

        try:
            from options_flow import get_options_snapshot
            snap = get_options_snapshot(symbol)

            score_bonus = 0
            is_gamma_squeeze = False
            reasons = []

            if snap:
                # 1. Call Wall Breach (Gamma Squeeze trigger)
                if snap.call_wall > 0 and current_price >= snap.call_wall * 0.99:
                    score_bonus += 25
                    is_gamma_squeeze = True
                    reasons.append(f"CALL_WALL_BREACH (${snap.call_wall:.2f})")

                # 2. Positive Net GEX (Dealer Buying Support)
                if snap.gex > 0:
                    score_bonus += 10
                    reasons.append("NET_GEX_POSITIVE")

                # 3. Low Put/Call Ratio (Bullish options bias)
                if 0 < snap.put_call_ratio < 0.65:
                    score_bonus += 15
                    reasons.append(f"BULLISH_PCR ({snap.put_call_ratio:.2f})")

            final_bonus = max(-20, min(35, score_bonus))
            logger.info("⚡ [GAMMA_RADAR] {}: Bonus {} pts | Squeeze: {} | Reasons: {}",
                        symbol, final_bonus, is_gamma_squeeze, reasons)

            return {
                "score_bonus": final_bonus,
                "is_gamma_squeeze": is_gamma_squeeze,
                "reasons": reasons
            }
        except Exception as e:
            logger.debug("GammaSqueezeRadar error for {}: {}", symbol, e)
            return {"score_bonus": 0, "is_gamma_squeeze": False, "reasons": []}
