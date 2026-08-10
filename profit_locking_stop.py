"""
[v9.0 DYNAMIC PROFIT-LOCKING TRAILING STOP MATRIX]
Dynamically locks in accrued unrealized profits so big winning trades NEVER turn into losses.

Profit Locking Thresholds:
- Gain >= +4.0%: Lock minimum +2.0% profit floor.
- Gain >= +8.0%: Lock minimum +5.5% profit floor.
- Gain >= +12.0%: Lock minimum +9.0% profit floor.
"""

from typing import Dict, Any
from loguru import logger


class ProfitLockingStopEngine:
    def __init__(self):
        pass

    def evaluate_profit_lock(self, symbol: str, entry_price: float, current_price: float, high_since_entry: float = 0.0) -> Dict[str, Any]:
        res = {
            'should_exit': False,
            'locked_stop_price': 0.0,
            'locked_profit_pct': 0.0,
            'reason': ''
        }

        if entry_price <= 0 or current_price <= 0:
            return res

        peak_price = max(current_price, high_since_entry or current_price)
        max_pnl_pct = (peak_price - entry_price) / entry_price * 100.0
        cur_pnl_pct = (current_price - entry_price) / entry_price * 100.0

        # Tier 3: +12% Peak Gain -> Lock +9.0% Floor
        if max_pnl_pct >= 12.0:
            floor_pct = 9.0
            stop_price = entry_price * (1.0 + floor_pct / 100.0)
            res['locked_stop_price'] = round(stop_price, 2)
            res['locked_profit_pct'] = floor_pct
            if current_price <= stop_price:
                res['should_exit'] = True
                res['reason'] = f"PROFIT_LOCK_TIER3: Peak +{max_pnl_pct:.1f}% -> Exited at +{cur_pnl_pct:.1f}% to lock +{floor_pct}% profit floor!"
                logger.info("🔒 [PROFIT_LOCK_EXIT] {}: {}", symbol, res['reason'])

        # Tier 2: +8% Peak Gain -> Lock +5.5% Floor
        elif max_pnl_pct >= 8.0:
            floor_pct = 5.5
            stop_price = entry_price * (1.0 + floor_pct / 100.0)
            res['locked_stop_price'] = round(stop_price, 2)
            res['locked_profit_pct'] = floor_pct
            if current_price <= stop_price:
                res['should_exit'] = True
                res['reason'] = f"PROFIT_LOCK_TIER2: Peak +{max_pnl_pct:.1f}% -> Exited at +{cur_pnl_pct:.1f}% to lock +{floor_pct}% profit floor!"
                logger.info("🔒 [PROFIT_LOCK_EXIT] {}: {}", symbol, res['reason'])

        # Tier 1: +4% Peak Gain -> Lock +2.0% Floor
        elif max_pnl_pct >= 4.0:
            floor_pct = 2.0
            stop_price = entry_price * (1.0 + floor_pct / 100.0)
            res['locked_stop_price'] = round(stop_price, 2)
            res['locked_profit_pct'] = floor_pct
            if current_price <= stop_price:
                res['should_exit'] = True
                res['reason'] = f"PROFIT_LOCK_TIER1: Peak +{max_pnl_pct:.1f}% -> Exited at +{cur_pnl_pct:.1f}% to lock +{floor_pct}% profit floor!"
                logger.info("🔒 [PROFIT_LOCK_EXIT] {}: {}", symbol, res['reason'])

        return res
