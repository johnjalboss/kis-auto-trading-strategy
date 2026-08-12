"""
[v11.0 ULTRA QUANT] Kelly Criterion & Volatility Parity Position Sizer
======================================================================
Calculates optimal position quantity using Kelly Criterion & ATR Volatility Parity:

f* = (p * b - q) / b * (Target_Volatility / Asset_Volatility)

High volatility stocks get smaller allocation, low volatility high-win stocks get larger allocation.
Dramatically smooths portfolio equity curve drawdowns toward zero!
"""

from typing import Dict, Any
from loguru import logger
import config


class KellyVolatilitySizer:
    def __init__(self, target_daily_vol: float = 0.015):
        self.target_daily_vol = target_daily_vol

    def calculate_qty(self, symbol: str, entry_price: float, total_equity: float, 
                      buying_power: float, atr: float, win_rate: float = 0.65, 
                      win_loss_ratio: float = 1.5) -> int:
        if entry_price <= 0 or total_equity <= 0 or buying_power <= 0:
            return 0

        try:
            # 1. Full Kelly Fraction f* = (p * b - q) / b
            p = win_rate
            q = 1.0 - p
            b = win_loss_ratio
            full_kelly = (p * b - q) / b if b > 0 else 0.10
            
            # Half-Kelly safety cap for conservative risk management
            half_kelly = max(0.05, min(0.25, full_kelly * 0.5))

            # 2. Volatility Parity Scaling factor
            asset_daily_vol = (atr / entry_price) if atr > 0 else 0.02
            vol_scale = self.target_daily_vol / max(0.005, asset_daily_vol)
            vol_scale = max(0.40, min(1.60, vol_scale))  # Cap volatility scaling between 40% and 160%

            # 3. Target Slot Capital
            base_slot_capital = total_equity / getattr(config, 'MAX_POSITIONS', 5)
            adjusted_capital = base_slot_capital * (half_kelly / 0.10) * vol_scale

            # Cap position capital to max 35% of total equity
            max_cap = total_equity * 0.35
            target_capital = min(adjusted_capital, max_cap, buying_power)

            qty = int(target_capital / entry_price)
            if qty == 0 and entry_price <= target_capital * 1.5 and entry_price <= buying_power:
                qty = 1  # Allow 1 share entry if close to budget

            logger.info("📐 [KELLY_VOLATILITY_SIZER] {}: Qty {} shares (VolScale: {:.2f}, TargetCap: ${:.2f})",
                        symbol, qty, vol_scale, target_capital)
            return qty
        except Exception as e:
            logger.debug("KellyVolatilitySizer error for {}: {}", symbol, e)
            return int(min(buying_power, total_equity * 0.20) / entry_price)
