"""
6. Factor Performance Attribution Engine (factor_attribution.py)
================================================================
Decomposes settled trade PnL into quantitative factor contributions:
- Momentum Factor Contribution
- Sector Tailwind Contribution
- PEAD Earnings Surprise Contribution
- Microstructure / Amihud Pressure Contribution
Used in Telegram exit receipt cards to provide crystal-clear performance explanations.
"""

from typing import Dict, Any, List
from loguru import logger

class FactorAttributionEngine:
    """Decomposes trade PnL into Factor Drivers"""

    def attribute(self, symbol: str, pnl_pct: float, entry_reason: str,
                  score_breakdown: List[str] = None) -> Dict[str, Any]:
        """
        Calculates estimated factor attribution percentages.
        """
        breakdown = score_breakdown or []
        breakdown_text = " ".join(breakdown) + " " + (entry_reason or "")

        weights = {
            "모멘텀/추세 팩터": 0.35,
            "섹터 로테이션 순풍": 0.25,
            "기관 수급/아미후드": 0.20,
            "어닝 서프라이즈 (PEAD)": 0.20,
        }

        # Adjust factor weights based on entry breakdown tags
        if "PEAD" in breakdown_text or "실적" in breakdown_text:
            weights["어닝 서프라이즈 (PEAD)"] = 0.40
            weights["모멘텀/추세 팩터"] = 0.25
        if "섹터" in breakdown_text or "순풍" in breakdown_text:
            weights["섹터 로테이션 순풍"] = 0.35
        if "아미후드" in breakdown_text or "수급" in breakdown_text:
            weights["기관 수급/아미후드"] = 0.30

        # Normalize weights
        total_w = sum(weights.values())
        norm_weights = {k: v / total_w for k, v in weights.items()}

        attributions = {}
        for factor, w in norm_weights.items():
            contrib = round(pnl_pct * w, 2)
            attributions[factor] = contrib

        return {
            "symbol": symbol,
            "total_pnl_pct": round(pnl_pct, 2),
            "factors": attributions
        }
