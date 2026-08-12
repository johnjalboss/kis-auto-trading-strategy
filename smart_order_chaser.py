"""
Smart Order Chaser Engine (smart_order_chaser.py)
=================================================
Monitors open orders and continuously reprices unfilled limit orders
to current market Ask/Bid price after a 15-second timeout, preventing missed fills on momentum breakouts.
"""

import time
from typing import Dict, Any, Optional
from loguru import logger

class SmartOrderChaser:
    def __init__(self, timeout_seconds: int = 15, max_drift_pct: float = 0.015):
        self.timeout_seconds = timeout_seconds
        self.max_drift_pct = max_drift_pct

    def evaluate_order(self, symbol: str, action: str, initial_price: float, current_price: float, elapsed_seconds: float) -> Dict[str, Any]:
        """
        Evaluates whether an open order should be repriced, kept, or cancelled.
        """
        if elapsed_seconds < self.timeout_seconds:
            return {"action": "WAIT", "new_price": initial_price, "reason": "Within timeout window"}

        drift_pct = (current_price - initial_price) / initial_price if initial_price > 0 else 0.0

        if action == "BUY":
            if drift_pct > self.max_drift_pct:
                logger.warning("⚡ [SMART_CHASER] {}: Price drifted +{:.2f}% (Limit: {:.2f}%). Cancelling to avoid top chasing.",
                               symbol, drift_pct * 100, self.max_drift_pct * 100)
                return {"action": "CANCEL", "new_price": current_price, "reason": "Max drift exceeded"}
            else:
                logger.info("⚡ [SMART_CHASER] {}: Repricing BUY order from ${:.2f} -> ${:.2f} (Ask Chasing)",
                            symbol, initial_price, current_price)
                return {"action": "REPRICE", "new_price": current_price, "reason": "15s limit chase"}
        else: # SELL
            if drift_pct < -self.max_drift_pct:
                logger.warning("⚡ [SMART_CHASER] {}: Price fell -{:.2f}%. Repricing SELL order to ${:.2f} to ensure exit.",
                               symbol, abs(drift_pct) * 100, current_price)
                return {"action": "REPRICE", "new_price": current_price, "reason": "Slippage exit chase"}
            else:
                return {"action": "REPRICE", "new_price": current_price, "reason": "Bid chase"}

def get_smart_chaser() -> SmartOrderChaser:
    return SmartOrderChaser()
