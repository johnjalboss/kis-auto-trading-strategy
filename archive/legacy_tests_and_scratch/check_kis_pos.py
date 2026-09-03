import sys
import os
from loguru import logger

# Add current dir to path
sys.path.append(os.getcwd())

from trader import get_trader
import config

def check_kis_positions():
    trader = get_trader()
    trader.start()
    
    print("Fetching positions from KIS...")
    positions = trader.get_positions()
    
    if not positions:
        print("No positions found in KIS.")
    else:
        for pos in positions:
            print(f"Symbol: {pos.symbol}, Qty: {pos.quantity}, AvgPrice: {pos.avg_price}, Current: {pos.current_price}, Exch: {pos.exchange}")
            
    trader.stop()

if __name__ == "__main__":
    check_kis_positions()
