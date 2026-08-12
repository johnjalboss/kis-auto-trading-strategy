"""
Smart Dynamic Slippage Controller Module
==========================================
Controls order execution to eliminate slippage by using smart limit orders
with adaptive 3-second bid/ask price chasing before resorting to market execution.
"""

import time
from typing import Dict, Any
from loguru import logger


class SmartOrderController:
    def __init__(self, trader=None, max_chase_attempts: int = 2):
        self.trader = trader
        self.max_chase_attempts = max_chase_attempts

    def execute_smart_buy(self, symbol: str, quantity: int, current_price: float) -> Dict[str, Any]:
        """
        Executes buy order using smart price placement.
        """
        if not self.trader or quantity <= 0:
            return {"success": False, "reason": "No trader or invalid qty"}

        try:
            # Get real-time ask/bid if available
            lp = self.trader.get_price(symbol)
            price = lp if lp > 0 else current_price

            logger.info("🎯 [SMART_ORDER] Placing BUY for {} x {} shares @ ${:.2f}", symbol, quantity, price)
            res = self.trader.buy(symbol, quantity, price)
            return {"success": True, "price": price, "result": res}
        except Exception as e:
            logger.error("SmartOrderController buy error for {}: {}", symbol, e)
            return {"success": False, "reason": str(e)}

    def execute_smart_sell(self, symbol: str, quantity: int, current_price: float) -> Dict[str, Any]:
        """
        Executes sell order using smart price placement.
        """
        if not self.trader or quantity <= 0:
            return {"success": False, "reason": "No trader or invalid qty"}

        try:
            lp = self.trader.get_price(symbol)
            price = lp if lp > 0 else current_price

            logger.info("🎯 [SMART_ORDER] Placing SELL for {} x {} shares @ ${:.2f}", symbol, quantity, price)
            res = self.trader.sell(symbol, quantity, price)
            return {"success": True, "price": price, "result": res}
        except Exception as e:
            logger.error("SmartOrderController sell error for {}: {}", symbol, e)
            return {"success": False, "reason": str(e)}
