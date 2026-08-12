"""
2026 Cutting-Edge Quant Module 2: Risk Parity Allocator (risk_parity_allocator.py)
====================================================================================
Implements Volatility Parity position sizing based on inverse ATR / volatility.
Scales position sizes dynamically to optimize portfolio Sharpe Ratio (>2.5 target).
"""

from typing import Dict, Any
from loguru import logger
import config
from safe_math import safe_div


class RiskParityAllocator:
    """Volatility Parity Capital Allocator (Bridgewater Style)."""

    def __init__(self, target_daily_vol: float = 0.018):
        self.target_daily_vol = target_daily_vol

    def calculate_risk_parity_qty(self, symbol: str, entry_price: float, total_equity: float,
                                   buying_power: float, atr: float) -> int:
        """
        Calculates position quantity inversely proportional to asset daily volatility.
        """
        if entry_price <= 0 or total_equity <= 0 or buying_power <= 0:
            return 0

        try:
            max_positions = getattr(config, 'MAX_POSITIONS', 5)
            base_slot_capital = safe_div(total_equity, max_positions, fallback=total_equity * 0.20)

            # Daily asset volatility = ATR / Entry Price
            asset_daily_vol = safe_div(atr, entry_price, fallback=0.02)
            
            # Risk Parity Scale Factor = Target Vol / Asset Vol
            vol_scale = safe_div(self.target_daily_vol, max(0.005, asset_daily_vol), fallback=1.0)
            vol_scale = max(0.50, min(1.50, vol_scale))  # Cap between 50% and 150%

            # Target Capital = Base Slot Capital * Vol Scale
            target_capital = min(base_slot_capital * vol_scale, buying_power)
            
            qty = int(safe_div(target_capital, entry_price, fallback=0))
            if qty == 0 and entry_price <= buying_power:
                qty = 1

            logger.info("⚖️ [RISK_PARITY] {}: Qty {} shares (VolScale: {:.2f}x, TargetCap: ${:.2f})",
                        symbol, qty, vol_scale, target_capital)
            return qty

        except Exception as e:
            logger.debug("RiskParityAllocator error for {}: {}", symbol, e)
            return int(safe_div(buying_power, entry_price, fallback=0))
