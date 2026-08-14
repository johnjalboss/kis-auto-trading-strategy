"""
3. Chandelier Volatility Exit Engine (chandelier_exit.py)
=========================================================
Academic / Practical Concept (Chuck LeBeau):
- Computes volatility-adaptive trailing stop based on Highest High since entry minus 3.0 * ATR(14).
- Formula: StopPrice = HighestHigh(N) - (multiplier * ATR_14)
- Allows winning momentum trades to run with maximum runway without premature whipsaw shakeouts.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from loguru import logger

class ChandelierExitEngine:
    """Evaluates Chandelier Volatility Trailing Stop Exits"""

    def __init__(self, atr_multiplier: float = 3.0, lookback: int = 14):
        self.multiplier = atr_multiplier
        self.lookback = lookback

    def evaluate_exit(self, symbol: str, entry_price: float, current_price: float,
                      highest_since_entry: float, atr: float) -> Dict[str, Any]:
        """
        Evaluate if current price breached the Chandelier stop level.
        """
        if highest_since_entry <= 0:
            highest_since_entry = max(entry_price, current_price)
        if atr <= 0:
            atr = entry_price * 0.02

        stop_price = highest_since_entry - (self.multiplier * atr)
        
        # Never allow stop price to be worse than initial hard stop (-6.0%)
        initial_floor = entry_price * 0.94
        effective_stop = max(stop_price, initial_floor)

        pnl_pct = ((current_price - entry_price) / entry_price) * 100.0
        peak_gain_pct = ((highest_since_entry - entry_price) / entry_price) * 100.0

        should_exit = (current_price <= effective_stop) and (peak_gain_pct >= 4.0)

        res = {
            "symbol": symbol,
            "current_price": round(current_price, 2),
            "highest_price": round(highest_since_entry, 2),
            "chandelier_stop": round(effective_stop, 2),
            "pnl_pct": round(pnl_pct, 2),
            "peak_gain_pct": round(peak_gain_pct, 2),
            "should_exit": should_exit,
            "reason": f"CHANDELIER_VOL_EXIT: Price ${current_price:.2f} <= Stop ${effective_stop:.2f} (Peak +{peak_gain_pct:.1f}%)" if should_exit else "HOLD"
        }
        return res
