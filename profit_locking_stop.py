"""
Profit Locking Stop Module (profit_locking_stop.py)
===================================================
Enforces tighter multi-tiered profit-locking stop floors to ensure unrealized gains are protected:
- PnL >= +3.0%: Stop floor locked at minimum +1.5% gain
- PnL >= +5.0%: Stop floor locked at minimum +3.0% gain
- PnL >= +8.0%: Stop floor locked at minimum +5.0% gain
- PnL >= +12.0%: Stop floor locked at minimum +8.0% gain
"""

from typing import Dict, Any
from loguru import logger

class ProfitLockingStop:
    def __init__(self, atr_multiplier: float = 2.0):
        self.atr_multiplier = atr_multiplier

    def calculate_locked_stop(self, entry_price: float, current_price: float, highest_price: float, atr: float) -> Dict[str, Any]:
        if entry_price <= 0 or current_price <= 0:
            return {"stop_price": 0.0, "type": "Invalid"}

        pnl_pct = ((current_price - entry_price) / entry_price) * 100.0
        peak_pnl = ((highest_price - entry_price) / entry_price) * 100.0 if highest_price > 0 else pnl_pct

        # 1. Chandelier Exit Base Stop (Highest High - 2.0 * ATR)
        chandelier_stop = highest_price - (self.atr_multiplier * atr) if atr > 0 else (entry_price * 0.94)
        stop_price = max(entry_price * 0.94, chandelier_stop)
        protection_type = "Chandelier ATR Trailing Stop"

        # 2. Multi-Tiered Profit Locking Floor Enforcement
        if peak_pnl >= 12.0 or pnl_pct >= 12.0:
            locked_floor = entry_price * 1.080 # Minimum +8.0% profit guaranteed
            if stop_price < locked_floor:
                stop_price = locked_floor
                protection_type = "Tier 4 Lock-In (+8.0% Guaranteed)"
        elif peak_pnl >= 8.0 or pnl_pct >= 8.0:
            locked_floor = entry_price * 1.050 # Minimum +5.0% profit guaranteed
            if stop_price < locked_floor:
                stop_price = locked_floor
                protection_type = "Tier 3 Lock-In (+5.0% Guaranteed)"
        elif peak_pnl >= 5.0 or pnl_pct >= 4.8: # Include near 5% (+4.8%)
            locked_floor = entry_price * 1.030 # Minimum +3.0% profit guaranteed
            if stop_price < locked_floor:
                stop_price = locked_floor
                protection_type = "Tier 2 Lock-In (+3.0% Guaranteed)"
        elif peak_pnl >= 3.0 or pnl_pct >= 3.0:
            locked_floor = entry_price * 1.015 # Minimum +1.5% profit guaranteed
            if stop_price < locked_floor:
                stop_price = locked_floor
                protection_type = "Tier 1 Lock-In (+1.5% Guaranteed)"

        logger.debug("🛡️ [PROFIT_LOCK] Entry: ${:.2f} | Curr: ${:.2f} ({:+.2f}%) | Stop: ${:.2f} ({})",
                     entry_price, current_price, pnl_pct, stop_price, protection_type)

        return {
            "stop_price": stop_price,
            "type": protection_type,
            "pnl_pct": pnl_pct
        }

    def evaluate_profit_lock(self, symbol: str, entry_price: float, current_price: float,
                             high_since_entry: float, atr: float = 0.0) -> Dict[str, Any]:
        """Evaluates whether current price has fallen below the profit-locked floor."""
        if entry_price <= 0 or current_price <= 0:
            return {"should_exit": False, "reason": "Invalid price"}

        res = self.calculate_locked_stop(entry_price, current_price, high_since_entry, atr)
        stop_price = res.get("stop_price", 0.0)
        pnl_pct = res.get("pnl_pct", 0.0)
        prot_type = res.get("type", "")

        # If locked floor is active and current price dropped below it, trigger exit!
        if "Lock-In" in prot_type and current_price <= stop_price:
            return {
                "should_exit": True,
                "reason": f"PROFIT_LOCK_EXIT: {prot_type} triggered at ${current_price:.2f} (Lock Floor: ${stop_price:.2f}, PnL: {pnl_pct:+.1f}%)"
            }

        return {"should_exit": False, "reason": "HOLD", "stop_price": stop_price}

ProfitLockingStopEngine = ProfitLockingStop

def get_profit_locking_stop() -> ProfitLockingStop:
    return ProfitLockingStop()
