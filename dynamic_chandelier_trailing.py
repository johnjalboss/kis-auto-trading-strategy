"""
dynamic_chandelier_trailing.py
================================================================================
Institutional Dynamic Chandelier Trailing Stop Engine ("Let Winners Run")
- Activates 'Trend Ride Mode' once position profit exceeds +7.0%
- Anchors trailing stop loss to:
    Trailing Stop = Highest Price Reached - (2.5 * ATR_14)
- Guarantees minimum locked profit:
    * +7% profit -> Minimum +3.5% locked
    * +12% profit -> Minimum +7.5% locked
    * +20% profit -> Minimum +14.0% locked
- Eliminates premature exits on mega-trend runners (e.g. +30~50% winners)
================================================================================
"""

import os
from typing import Dict, Any, Tuple, Optional
from loguru import logger

class DynamicChandelierTrailing:
    def __init__(self, activation_profit_pct: float = 7.0, atr_multiplier: float = 2.5):
        self.activation_profit_pct = activation_profit_pct
        self.atr_multiplier = atr_multiplier
        # Stores highest price tracked per position: {symbol: highest_price}
        self.peak_prices: Dict[str, float] = {}

    def update_peak_price(self, symbol: str, current_price: float, entry_price: float) -> float:
        """Updates and returns the highest price reached since entry."""
        current_peak = self.peak_prices.get(symbol, entry_price)
        if current_price > current_peak:
            current_peak = current_price
            self.peak_prices[symbol] = current_peak
        return current_peak

    def calculate_exit_thresholds(
        self,
        symbol: str,
        entry_price: float,
        current_price: float,
        atr_14: float = 0.0,
        base_stop_loss: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculates dynamic trailing stop and profit-lock levels.
        """
        if entry_price <= 0 or current_price <= 0:
            return {"should_exit": False, "reason": "INVALID_PRICE"}

        pnl_pct = ((current_price / entry_price) - 1.0) * 100.0
        peak_price = self.update_peak_price(symbol, current_price, entry_price)
        peak_pnl_pct = ((peak_price / entry_price) - 1.0) * 100.0

        # Approximate ATR if not provided (default 2.5% of price)
        if atr_14 <= 0:
            atr_14 = current_price * 0.025

        # Check if Trend Ride Mode is Active
        is_trend_ride_active = (peak_pnl_pct >= self.activation_profit_pct)

        if is_trend_ride_active:
            # 1. Chandelier Trailing Stop Level
            chandelier_stop = peak_price - (self.atr_multiplier * atr_14)

            # 2. Tiered Profit Ratchet Guarantee Floor
            if peak_pnl_pct >= 20.0:
                guaranteed_floor = entry_price * 1.14      # Lock in +14%
            elif peak_pnl_pct >= 12.0:
                guaranteed_floor = entry_price * 1.075     # Lock in +7.5%
            else:
                guaranteed_floor = entry_price * 1.035     # Lock in +3.5%

            effective_stop = max(chandelier_stop, guaranteed_floor, base_stop_loss)

            if current_price <= effective_stop:
                return {
                    "should_exit": True,
                    "action": "TRAILING_STOP_TAKE_PROFIT",
                    "reason": f"샹들리에 트레일링 스탑 도달 (+{pnl_pct:.1f}% 확정, 고점 ${peak_price:.2f} 대비 조정)",
                    "effective_stop": round(effective_stop, 2),
                    "is_trend_ride": True,
                    "pnl_pct": round(pnl_pct, 2)
                }
            else:
                return {
                    "should_exit": False,
                    "action": "HOLD_TREND_RIDE",
                    "reason": f"추세 추종(Trend Ride) 유지 중 (고점 ${peak_price:.2f}, 추적손절가 ${effective_stop:.2f})",
                    "effective_stop": round(effective_stop, 2),
                    "is_trend_ride": True,
                    "pnl_pct": round(pnl_pct, 2)
                }

        # Regular Stop Loss check
        if base_stop_loss > 0 and current_price <= base_stop_loss:
            return {
                "should_exit": True,
                "action": "BASE_STOP_LOSS",
                "reason": f"기본 손절 라인 (${base_stop_loss:.2f}) 도달",
                "effective_stop": round(base_stop_loss, 2),
                "is_trend_ride": False,
                "pnl_pct": round(pnl_pct, 2)
            }

        return {
            "should_exit": False,
            "action": "HOLD",
            "reason": "정상 보유 중",
            "effective_stop": round(base_stop_loss, 2),
            "is_trend_ride": False,
            "pnl_pct": round(pnl_pct, 2)
        }

    def clear_position(self, symbol: str):
        """Cleans up memory when position is fully closed."""
        self.peak_prices.pop(symbol, None)

if __name__ == "__main__":
    engine = DynamicChandelierTrailing()
    # Test case: bought at $100, rose to $115, now at $112
    res = engine.calculate_exit_thresholds("NVDA", entry_price=100.0, current_price=112.0, atr_14=2.0)
    print("Test Result:", res)
