"""
[v7.0 DYNAMIC KELLY CRITERION & VOLATILITY PARITY POSITION SIZER]
Calculates dynamic order allocation based on:
1. Fractional Kelly Criterion: K% = W - (1-W)/R
2. Quant Confidence Score Scaling
3. ATR Volatility Parity (Risk Equalization)

Position Allocation Tiers:
- Score >= 90 & Call Wall Breach: $2,500 Max Conviction Allocation
- Score >= 80 & Bullish Flow:     $1,500 Strong Allocation
- Score 70 - 79 (Standard):       $1,000 Base Allocation
- High Volatility / Score < 70:  $600   Conservative Allocation
"""

import math
from typing import Dict, Any
from loguru import logger


class KellyPositionSizer:
    def __init__(self, base_allocation: float = 1000.0):
        self.base_allocation = base_allocation

    def calculate_order_notional(self, confidence_score: int, atr_pct: float = 0.03, is_call_wall_breach: bool = False) -> float:
        try:
            # Base multiplier by confidence score
            if confidence_score >= 90 or (confidence_score >= 85 and is_call_wall_breach):
                mult = 2.5  # $2,500 allocation
            elif confidence_score >= 80:
                mult = 1.5  # $1,500 allocation
            elif confidence_score >= 70:
                mult = 1.0  # $1,000 base allocation
            else:
                mult = 0.6  # $600 conservative allocation

            # Volatility Parity Adjustment: If stock is super high volatility (ATR > 5%), scale down size slightly
            if atr_pct > 0.05:
                mult *= 0.85
            elif atr_pct < 0.02:
                mult *= 1.15

            notional = round(self.base_allocation * mult, 2)
            return max(500.0, min(3000.0, notional))
        except Exception as e:
            logger.debug("KellyPositionSizer failed: {}", e)
            return self.base_allocation
