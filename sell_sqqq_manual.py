from trader import Trader
from smart_order import get_smart_executor

trader = Trader()  
executor = get_smart_executor(trader)

print("Selling SQQQ (1 share)...")
try:
    # Use Trader.sell directly for Market Order:
    # The signature in this version is def sell(self, symbol: str, quantity: int, limit_price: float = None)
    # The 'SLL_TYPE': '00' inside trader.sell sends a limit order by default. Let's send a lower limit to ensure execution.
    # Current SQQQ price is around 71. So 70.0 as limit price to force it.
    order = trader.sell("SQQQ", 1, 70.0)
    print(f"Order Executed: {order}")
except Exception as e:
    print(f"Sell failed: {e}")
