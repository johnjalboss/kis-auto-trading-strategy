"""
Dynamic Ratchet Take-Profit Ladder (dynamic_ratchet_take_profit.py)
===================================================================
Adaptive profit-locking ladder engine tailored to each stock's volatility profile:
- Low-Volatility Value/Defensive Stocks (ATR < 2.0% e.g. MRK, JNJ): Tiered lock (+2.0%, +5.5%, +8.0%)
- High-Volatility Growth Leaders (ATR >= 3.0% e.g. NVDA, LLY): Ratchet ladder (1.5R -> 2.5R -> 4.0R)
  allowing super-winners to run up to 20~30%+ while securing capital on sharp pullbacks.
"""

from typing import Dict, Any, Optional
import math
from loguru import logger


class DynamicRatchetTakeProfitLadder:
    """Calculates adaptive profit targets and ratchet floor locks."""

    def evaluate_exit(self, symbol: str, entry_price: float, current_price: float,
                      high_since_entry: float, atr: float = 0.0,
                      regime: str = "BULL_NORMAL") -> Dict[str, Any]:
        default_res = {
            "should_exit": False,
            "exit_type": "NONE",
            "reason": "",
            "ratchet_floor_price": 0.0,
            "target_tier": 0
        }

        if entry_price <= 0 or current_price <= 0:
            return default_res

        try:
            pnl_pct = (current_price - entry_price) / entry_price
            peak_pnl_pct = (high_since_entry - entry_price) / entry_price if high_since_entry > entry_price else pnl_pct
            atr_pct = (atr / entry_price) if (atr > 0 and entry_price > 0) else 0.020

            # Volatility classification
            is_low_vol = atr_pct < 0.022  # e.g., MRK, JNJ, ABBV (~1.5% ATR)
            is_high_vol = atr_pct >= 0.035  # e.g., NVDA, PLTR, AMD (3.5%+ ATR)

            # -------------------------------------------------------------
            # Case 1: Low-Volatility Stocks (Quick Cash-Out & Tight Locks)
            # -------------------------------------------------------------
            if is_low_vol:
                # Tier 3: Peak >= +8.0% -> Lock in at least +6.0%
                if peak_pnl_pct >= 0.080:
                    floor_price = entry_price * 1.060
                    if current_price <= floor_price:
                        return {
                            "should_exit": True,
                            "exit_type": "SELL_ALL",
                            "reason": f"LOW_VOL_TIER3_LOCK: Peak {peak_pnl_pct:+.1%}, lock exit at {pnl_pct:+.1%}",
                            "ratchet_floor_price": floor_price,
                            "target_tier": 3
                        }
                # Tier 2: Peak >= +5.5% -> Lock in at least +4.0%
                elif peak_pnl_pct >= 0.055:
                    floor_price = entry_price * 1.040
                    if current_price <= floor_price:
                        return {
                            "should_exit": True,
                            "exit_type": "SELL_ALL",
                            "reason": f"LOW_VOL_TIER2_LOCK: Peak {peak_pnl_pct:+.1%}, lock exit at {pnl_pct:+.1%}",
                            "ratchet_floor_price": floor_price,
                            "target_tier": 2
                        }
                # Tier 1: Peak >= +2.0% -> Protect Breakeven (+0.8%)
                elif peak_pnl_pct >= 0.020:
                    floor_price = entry_price * 1.008
                    if current_price <= floor_price:
                        return {
                            "should_exit": True,
                            "exit_type": "SELL_ALL",
                            "reason": f"LOW_VOL_TIER1_LOCK: Peak {peak_pnl_pct:+.1%}, breakeven lock at {pnl_pct:+.1%}",
                            "ratchet_floor_price": floor_price,
                            "target_tier": 1
                        }

            # -------------------------------------------------------------
            # Case 2: High-Momentum Growth Super-Leaders (Let Winners Run)
            # -------------------------------------------------------------
            elif is_high_vol:
                # Mega Tier 4: Peak >= +25.0% -> Lock in at least +20.0%
                if peak_pnl_pct >= 0.250:
                    floor_price = entry_price * 1.200
                    if current_price <= floor_price:
                        return {
                            "should_exit": True,
                            "exit_type": "SELL_ALL",
                            "reason": f"MEGA_LEADER_RATCHET_20PCT: Peak {peak_pnl_pct:+.1%}, locked profit at {pnl_pct:+.1%}",
                            "ratchet_floor_price": floor_price,
                            "target_tier": 4
                        }
                # Super Tier 3: Peak >= +14.0% -> Lock in at least +10.5%
                elif peak_pnl_pct >= 0.140:
                    floor_price = entry_price * 1.105
                    if current_price <= floor_price:
                        return {
                            "should_exit": True,
                            "exit_type": "SELL_ALL",
                            "reason": f"HIGH_VOL_RATCHET_10PCT: Peak {peak_pnl_pct:+.1%}, locked profit at {pnl_pct:+.1%}",
                            "ratchet_floor_price": floor_price,
                            "target_tier": 3
                        }
                # Tier 2: Peak >= +8.0% -> Lock in at least +5.5%
                elif peak_pnl_pct >= 0.080:
                    floor_price = entry_price * 1.055
                    if current_price <= floor_price:
                        return {
                            "should_exit": True,
                            "exit_type": "SELL_ALL",
                            "reason": f"HIGH_VOL_RATCHET_5PCT: Peak {peak_pnl_pct:+.1%}, locked profit at {pnl_pct:+.1%}",
                            "ratchet_floor_price": floor_price,
                            "target_tier": 2
                        }
                # Tier 1: Peak >= +4.0% -> Protect Breakeven (+1.5%)
                elif peak_pnl_pct >= 0.040:
                    floor_price = entry_price * 1.015
                    if current_price <= floor_price:
                        return {
                            "should_exit": True,
                            "exit_type": "SELL_ALL",
                            "reason": f"HIGH_VOL_BREAKEVEN_PROTECT: Peak {peak_pnl_pct:+.1%}, protect exit at {pnl_pct:+.1%}",
                            "ratchet_floor_price": floor_price,
                            "target_tier": 1
                        }

            # -------------------------------------------------------------
            # Case 3: Standard Mid-Volatility Stocks
            # -------------------------------------------------------------
            else:
                if peak_pnl_pct >= 0.100:
                    floor_price = entry_price * 1.075
                    if current_price <= floor_price:
                        return {
                            "should_exit": True,
                            "exit_type": "SELL_ALL",
                            "reason": f"STD_RATCHET_TIER2: Peak {peak_pnl_pct:+.1%}, lock at {pnl_pct:+.1%}",
                            "ratchet_floor_price": floor_price,
                            "target_tier": 2
                        }
                elif peak_pnl_pct >= 0.035:
                    floor_price = entry_price * 1.012
                    if current_price <= floor_price:
                        return {
                            "should_exit": True,
                            "exit_type": "SELL_ALL",
                            "reason": f"STD_RATCHET_TIER1: Peak {peak_pnl_pct:+.1%}, lock at {pnl_pct:+.1%}",
                            "ratchet_floor_price": floor_price,
                            "target_tier": 1
                        }

            return default_res
        except Exception as e:
            logger.debug("DynamicRatchetTakeProfitLadder failed for {}: {}", symbol, e)
            return default_res
