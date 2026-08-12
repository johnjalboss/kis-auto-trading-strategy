"""
Profit-Locking Floor Engine (Risk-Free Trade & Profit Locking Matrix)
======================================================================
1. Breakeven Stop Trigger (+3.5% gain) -> Raises stop loss to Entry + 0.5% (Risk-Free Trade!).
2. Tier 1 Profit Lock (+7.0% gain)     -> Locks in +3.5% profit floor.
3. Tier 2 Profit Lock (+12.0% gain)    -> Locks in +7.0% profit floor.
4. Tier 3 Profit Lock (+18.0% gain)    -> Locks in +12.0% profit floor.
5. High-Peak Trailing Lock             -> Pullback > 3.0% from ATH peak exits for max profit capture.
"""

from loguru import logger
import config

class ProfitLockingStopEngine:
    """Dynamic Risk-Free Profit Floor Locking Engine"""

    def evaluate_profit_lock(self, symbol: str, entry_price: float, current_price: float, high_since_entry: float) -> dict:
        res = {
            "should_exit": False,
            "reason": "",
            "recommended_stop": 0.0,
            "is_risk_free": False
        }

        if entry_price <= 0 or current_price <= 0:
            return res

        pnl_pct = (current_price - entry_price) / entry_price
        max_pnl_pct = (high_since_entry - entry_price) / entry_price if high_since_entry > entry_price else pnl_pct

        # 1. Breakeven Stop (+3.5% trigger -> +0.5% floor)
        BREAKEVEN_TRIGGER = getattr(config, 'BREAKEVEN_STOP_TRIGGER', 0.035)
        if max_pnl_pct >= BREAKEVEN_TRIGGER:
            res["is_risk_free"] = True
            res["recommended_stop"] = entry_price * 1.005  # +0.5% floor

            # Check if current price dropped below breakeven floor
            if current_price <= res["recommended_stop"]:
                res["should_exit"] = True
                res["reason"] = f"🛡️ [BREAKEVEN_PROFIT_LOCK] Price dropped to ${current_price:.2f} (Floor: ${res['recommended_stop']:.2f}) - Exiting with +0.5% profit to preserve capital!"
                logger.info(res["reason"])
                return res

        # 2. Tier 1 Profit Lock (+7.0% trigger -> +3.5% floor)
        if max_pnl_pct >= 0.070:
            res["recommended_stop"] = entry_price * 1.035
            if current_price <= res["recommended_stop"]:
                res["should_exit"] = True
                res["reason"] = f"💰 [TIER_1_PROFIT_LOCK] Price dropped to ${current_price:.2f} (Floor: ${res['recommended_stop']:.2f}) - Locking in +3.5% profit!"
                logger.info(res["reason"])
                return res

        # 3. Tier 2 Profit Lock (+12.0% trigger -> +7.0% floor)
        if max_pnl_pct >= 0.120:
            res["recommended_stop"] = entry_price * 1.070
            if current_price <= res["recommended_stop"]:
                res["should_exit"] = True
                res["reason"] = f"💰💰 [TIER_2_PROFIT_LOCK] Price dropped to ${current_price:.2f} (Floor: ${res['recommended_stop']:.2f}) - Locking in +7.0% profit!"
                logger.info(res["reason"])
                return res

        # 4. Tier 3 Profit Lock (+18.0% trigger -> +12.0% floor)
        if max_pnl_pct >= 0.180:
            res["recommended_stop"] = entry_price * 1.120
            if current_price <= res["recommended_stop"]:
                res["should_exit"] = True
                res["reason"] = f"🏆 [TIER_3_PROFIT_LOCK] Price dropped to ${current_price:.2f} (Floor: ${res['recommended_stop']:.2f}) - Locking in +12.0% profit!"
                logger.info(res["reason"])
                return res

        # 5. Peak Trailing Pullback Lock (After +10.0% gain, 3.0% pullback from peak triggers exit)
        if max_pnl_pct >= 0.100 and high_since_entry > 0:
            peak_pullback = (high_since_entry - current_price) / high_since_entry
            if peak_pullback >= 0.030:
                res["should_exit"] = True
                res["reason"] = f"🔥 [PEAK_TRAILING_PROFIT_CAPTURE] Pulled back {peak_pullback*100:.1f}% from peak (${high_since_entry:.2f}) - Exiting to lock in max profit!"
                logger.info(res["reason"])
                return res

        return res
