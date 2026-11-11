"""
Profit Locking Stop Module (profit_locking_stop.py)
===================================================
Enforces institutional multi-tiered profit-locking stop floors for Pure Swing Trading (2-10 days horizon).
Calibrated to prevent "False Choke":
- Never lock tight micro-floors on normal intraday fluctuations (+0% ~ +3.5%).
- Allow swing breathing room so high-conviction positions can run to +5% ~ +15% targets.
- Once peak gain crosses +4.0%, arm guaranteed profit lock floor (Entry + 1.2% covers all fees & slippage).
- Smoothly scale up profit retention as gains expand.
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
        # SWING CALIBRATION: Give positions room to breathe until +4.0% gain.
        # Micro-locking at +1.8% or +2.5% caused premature stop-outs with near-zero (+0.05%~+0.5%) gains due to slippage.
        if peak_pnl >= 100.0 or pnl_pct >= 100.0:
            locked_floor = entry_price * 1.820  # Minimum +82.0% profit guaranteed
            if stop_price < locked_floor:
                stop_price = locked_floor
                protection_type = "Tier 9 Mega-Lock (+82.0% Guaranteed)"
        elif peak_pnl >= 80.0 or pnl_pct >= 80.0:
            locked_floor = entry_price * 1.650  # Minimum +65.0% profit guaranteed
            if stop_price < locked_floor:
                stop_price = locked_floor
                protection_type = "Tier 8 Mega-Lock (+65.0% Guaranteed)"
        elif peak_pnl >= 50.0 or pnl_pct >= 50.0:
            locked_floor = entry_price * 1.400  # Minimum +40.0% profit guaranteed
            if stop_price < locked_floor:
                stop_price = locked_floor
                protection_type = "Tier 7 Super-Lock (+40.0% Guaranteed)"
        elif peak_pnl >= 35.0 or pnl_pct >= 35.0:
            locked_floor = entry_price * 1.260  # Minimum +26.0% profit guaranteed
            if stop_price < locked_floor:
                stop_price = locked_floor
                protection_type = "Tier 6 Super-Lock (+26.0% Guaranteed)"
        elif peak_pnl >= 20.0 or pnl_pct >= 20.0:
            locked_floor = entry_price * 1.150  # Minimum +15.0% profit guaranteed
            if stop_price < locked_floor:
                stop_price = locked_floor
                protection_type = "Tier 5 Lock-In (+15.0% Guaranteed)"
        elif peak_pnl >= 15.0 or pnl_pct >= 15.0:
            locked_floor = entry_price * 1.110  # Minimum +11.0% profit guaranteed
            if stop_price < locked_floor:
                stop_price = locked_floor
                protection_type = "Tier 4.5 Lock-In (+11.0% Guaranteed)"
        elif peak_pnl >= 10.0 or pnl_pct >= 9.5:
            locked_floor = entry_price * 1.070  # Minimum +7.0% profit guaranteed
            if stop_price < locked_floor:
                stop_price = locked_floor
                protection_type = "Tier 4 Lock-In (+7.0% Guaranteed)"
        elif peak_pnl >= 7.0 or pnl_pct >= 6.8:
            locked_floor = entry_price * 1.045  # Minimum +4.5% profit guaranteed
            if stop_price < locked_floor:
                stop_price = locked_floor
                protection_type = "Tier 3 Lock-In (+4.5% Guaranteed)"
        elif peak_pnl >= 5.5 or pnl_pct >= 5.2:
            locked_floor = entry_price * 1.030  # Minimum +3.0% profit guaranteed
            if stop_price < locked_floor:
                stop_price = locked_floor
                protection_type = "Tier 2 Lock-In (+3.0% Guaranteed)"
        elif peak_pnl >= 4.0 or pnl_pct >= 3.8:
            locked_floor = entry_price * 1.015  # Minimum +1.5% profit guaranteed (covers 0.3% slippage + fees with solid net green)
            if stop_price < locked_floor:
                stop_price = locked_floor
                protection_type = "Tier 1 Breakeven-Plus Lock (+1.5% Guaranteed Net)"

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
