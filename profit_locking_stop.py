"""
Profit Locking Stop Module (profit_locking_stop.py)
===================================================
Enforces institutional multi-tiered profit-locking stop floors.
User Directive: If peak gain reaches +2.5%, the system MUST preserve at least +1.5% NET profit in the pocket!
Accounts for market-order execution slippage (~0.2%~0.3%) & KIS fees by setting the stop trigger floor at +1.8%.
"""

from typing import Dict, Any
from loguru import logger

class ProfitLockingStop:
    def __init__(self, atr_multiplier: float = 2.0):
        self.atr_multiplier = atr_multiplier

    def calculate_locked_stop(self, entry_price: float, current_price: float, highest_price: float, atr: float = 0.0) -> Dict[str, Any]:
        if entry_price <= 0 or current_price <= 0:
            return {"stop_price": 0.0, "type": "Invalid", "pnl_pct": 0.0}

        pnl_pct = ((current_price - entry_price) / entry_price) * 100.0
        peak_pnl = ((highest_price - entry_price) / entry_price) * 100.0 if highest_price > 0 else pnl_pct

        # 1. Chandelier Exit Base Stop (Highest High - 2.0 * ATR)
        chandelier_stop = highest_price - (self.atr_multiplier * atr) if atr > 0 else (entry_price * 0.955)
        stop_price = max(entry_price * 0.955, chandelier_stop)
        protection_type = "Chandelier ATR Trailing Stop"

        # 2. Multi-Tiered Profit Locking Floor Enforcement
        # USER DIRECTIVE: Peak +2.5% MUST secure at least +1.5% net profit after slippage & fees!
        # Trigger floor set at +1.8% so that 0.2%~0.3% slippage still leaves +1.5%~+1.6% net profit.
        if peak_pnl >= 100.0 or pnl_pct >= 100.0:
            locked_floor = entry_price * 1.850  # Minimum +85.0% profit guaranteed
            if stop_price < locked_floor:
                stop_price = locked_floor
                protection_type = "Tier 9 Mega-Lock (+85.0% Guaranteed)"
        elif peak_pnl >= 50.0 or pnl_pct >= 50.0:
            locked_floor = entry_price * 1.420  # Minimum +42.0% profit guaranteed
            if stop_price < locked_floor:
                stop_price = locked_floor
                protection_type = "Tier 7 Super-Lock (+42.0% Guaranteed)"
        elif peak_pnl >= 20.0 or pnl_pct >= 20.0:
            locked_floor = entry_price * 1.165  # Minimum +16.5% profit guaranteed
            if stop_price < locked_floor:
                stop_price = locked_floor
                protection_type = "Tier 5 Lock-In (+16.5% Guaranteed)"
        elif peak_pnl >= 15.0 or pnl_pct >= 15.0:
            locked_floor = entry_price * 1.125  # Minimum +12.5% floor (Net ~+12.0%)
            if stop_price < locked_floor:
                stop_price = locked_floor
                protection_type = "Tier 4.5 Lock-In (+12.5% Guaranteed)"
        elif peak_pnl >= 10.0 or pnl_pct >= 9.5:
            locked_floor = entry_price * 1.080  # Minimum +8.0% floor (Net ~+7.7%)
            if stop_price < locked_floor:
                stop_price = locked_floor
                protection_type = "Tier 4 Lock-In (+8.0% Guaranteed)"
        elif peak_pnl >= 7.0 or pnl_pct >= 6.8:
            locked_floor = entry_price * 1.055  # Minimum +5.5% floor (Net ~+5.2%)
            if stop_price < locked_floor:
                stop_price = locked_floor
                protection_type = "Tier 3 Lock-In (+5.5% Guaranteed)"
        elif peak_pnl >= 5.0 or pnl_pct >= 4.8:
            locked_floor = entry_price * 1.038  # Minimum +3.8% floor (Net ~+3.5%)
            if stop_price < locked_floor:
                stop_price = locked_floor
                protection_type = "Tier 2.5 Lock-In (+3.8% Guaranteed)"
        elif peak_pnl >= 3.5 or pnl_pct >= 3.3:
            locked_floor = entry_price * 1.025  # Minimum +2.5% floor (Net ~+2.2%)
            if stop_price < locked_floor:
                stop_price = locked_floor
                protection_type = "Tier 2 Lock-In (+2.5% Guaranteed)"
        elif peak_pnl >= 2.5 or pnl_pct >= 2.3:
            locked_floor = entry_price * 1.018  # Minimum +1.8% floor -> Guarantees Net +1.5% after slippage!
            if stop_price < locked_floor:
                stop_price = locked_floor
                protection_type = "Tier 1 Net Profit Lock (+1.8% Floor -> Net +1.5% Guaranteed)"

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
        if ("Lock" in prot_type or "Breakeven" in prot_type) and current_price <= stop_price:
            return {
                "should_exit": True,
                "reason": f"PROFIT_LOCK_EXIT: {prot_type} triggered at ${current_price:.2f} (Lock Floor: ${stop_price:.2f}, PnL: {pnl_pct:+.1f}%)"
            }

        return {"should_exit": False, "reason": "HOLD", "stop_price": stop_price}

ProfitLockingStopEngine = ProfitLockingStop

def get_profit_locking_stop() -> ProfitLockingStop:
    return ProfitLockingStop()
