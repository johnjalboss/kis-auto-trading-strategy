import sys
import os
from loguru import logger

# Add current dir to path
sys.path.append(os.getcwd())

from trader import get_trader
import config

def check_unfilled():
    trader = get_trader()
    trader.start()
    
    print("Fetching unfilled orders from KIS...")
    orders = trader.get_unfilled_orders()
    
    if not orders:
        print("No unfilled orders found.")
    else:
        for order in orders:
            print(f"OrderID: {order['order_id']}, Symbol: {order['symbol']}, Side: {order['side']}, Qty: {order['quantity']}, Price: {order['price']}")
            
    trader.stop()

if __name__ == "__main__":
    check_unfilled()
