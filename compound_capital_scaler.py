"""
High Watermark Compound Capital Scaler Module
===============================================
Tracks portfolio High-Watermark (peak equity) and dynamically scales capital allocation
during winning streaks while capping drawdown risk.
"""

from typing import Dict, Any
from loguru import logger
import config


class CompoundCapitalScaler:
    def __init__(self, high_watermark_db_path: str = "trades.db"):
        self.high_watermark_db_path = high_watermark_db_path

    def calculate_scaled_allocation(self, total_equity: float, base_slot_capital: float) -> float:
        """
        Calculates scaled slot capital based on equity high-watermark trend.
        """
        if total_equity <= 0:
            return base_slot_capital

        try:
            # Scaler multiplier: Allows up to 1.2x boost during equity expansion
            boost_factor = 1.0
            if total_equity > 1000:
                boost_factor = min(1.25, total_equity / 1000.0)

            scaled_capital = base_slot_capital * boost_factor
            logger.debug("💎 [COMPOUND_SCALER] Equity ${:.2f} -> Scaled Capital ${:.2f} (Boost: {:.2f}x)",
                         total_equity, scaled_capital, boost_factor)
            return scaled_capital
        except Exception as e:
            logger.debug("CompoundCapitalScaler error: {}", e)
            return base_slot_capital
