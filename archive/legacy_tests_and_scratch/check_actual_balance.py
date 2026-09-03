import os
import sys
from dotenv import load_dotenv

# Add current dir to path to import local modules
sys.path.append(os.getcwd())

from trader import get_trader
import config

def check_balance():
    # Force load .env
    load_dotenv()
    
    print(f"Checking balance for Account: {os.getenv('KIS_CANO')}")
    print(f"Environment: {os.getenv('TRADING_ENV')}")
    
    trader = get_trader()
    # trader.start() # Avoid background thread hang
    
    try:
        positions = trader.get_positions()
        if not positions:
            print("No positions found.")
        else:
            for pos in positions:
                print(f"SYMBOL: {pos.symbol}, QTY: {pos.quantity}, AVG: {pos.avg_price}, CURRENT: {pos.current_price}")
    except Exception as e:
        print(f"Error: {e}")
    # finally:
    #     trader.stop()

if __name__ == "__main__":
    check_balance()
