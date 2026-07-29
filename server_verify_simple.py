import os
import sys

sys.path.append(os.getcwd())
import config
from trader import get_trader

def verify_visibility():
    trader = get_trader()
    positions = trader.get_positions()
    symbols = [p.symbol for p in positions]
    print(f"FOUND SYMBOLS: {symbols}")
    
    for p in positions:
        print(f"SYM: {p.symbol:10} QTY: {p.quantity:5} AVG: {p.avg_price:10.2f} CURR: {p.current_price:10.2f} EXC: {p.exchange}")

if __name__ == "__main__":
    verify_visibility()
