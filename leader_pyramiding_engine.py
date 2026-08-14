"""
4. Leader Pyramiding Scale-In Engine (leader_pyramiding_engine.py)
==================================================================
Concept (Jesse Livermore / Institutional Pyramiding):
- When an existing position achieves a confirmed gain >= +4.0%:
  1. The stop loss for Tranche 1 is moved up to Break-Even (Entry Price + 0.5% buffer) -> 0% Risk Trade!
  2. A secondary scale-in tranche (+30% of target slot capital) is authorized to compound winners.
- Turns winning high-beta leaders into explosive compounders without ever adding risk to original capital.
"""

from typing import Dict, Any, List
from loguru import logger

class LeaderPyramidingEngine:
    """Evaluates Pyramiding / Scale-In opportunities for confirmed winning leaders"""

    def __init__(self, min_gain_pct: float = 4.0, max_scale_in_count: int = 1):
        self.min_gain_pct = min_gain_pct
        self.max_scale_ins = max_scale_in_count
        self._pyramided_symbols = set()

    def check_pyramiding_candidate(self, symbol: str, entry_price: float, current_price: float,
                                   existing_qty: int, buying_power: float, score: int = 80) -> Dict[str, Any]:
        """
        Check if an open position qualifies for a risk-free pyramiding scale-in tranche.
        """
        res = {
            "symbol": symbol,
            "can_scale_in": False,
            "scale_in_qty": 0,
            "new_breakeven_stop": 0.0,
            "unrealized_gain_pct": 0.0,
            "reason": "NOT_QUALIFIED"
        }

        if entry_price <= 0 or current_price <= 0 or existing_qty <= 0:
            return res

        gain_pct = ((current_price - entry_price) / entry_price) * 100.0
        res["unrealized_gain_pct"] = round(gain_pct, 2)

        if symbol.upper() in self._pyramided_symbols:
            res["reason"] = "ALREADY_PYRAMIDED"
            return res

        # Qualification: Gain >= +4.0% and score >= 75
        if gain_pct >= self.min_gain_pct and score >= 75:
            # Move tranche 1 stop loss to entry price + 0.5%
            breakeven_stop = round(entry_price * 1.005, 2)
            res["new_breakeven_stop"] = breakeven_stop

            # Scale-in tranche size: 30% of existing shares
            scale_qty = max(1, int(existing_qty * 0.30))
            required_cash = scale_qty * current_price

            if buying_power >= required_cash:
                res["can_scale_in"] = True
                res["scale_in_qty"] = scale_qty
                res["reason"] = f"LEADER_PYRAMID_SCALE_IN: Unrealized Gain +{gain_pct:.1f}%, Breakeven Stop @ ${breakeven_stop:.2f}"
                logger.info("🔥 [LEADER_PYRAMIDING] {} qualified for 30% Scale-In Tranche (Gain +{:.1f}%) -> Stop moved to ${:.2f}",
                            symbol, gain_pct, breakeven_stop)
            else:
                res["reason"] = f"INSUFFICIENT_BP_FOR_SCALE_IN (Need ${required_cash:.2f}, Have ${buying_power:.2f})"

        return res

    def mark_pyramided(self, symbol: str):
        self._pyramided_symbols.add(symbol.upper())
