import os
import sys

sys.path.append(os.getcwd())
from trader import get_trader

def audit():
    trader = get_trader()
    positions = trader.get_positions()
    print("--- LIVE KIS POSITIONS ---")
    for p in positions:
        pnl = (p.current_price / p.avg_price - 1) * 100 if p.avg_price > 0 else 0
        print(f"SYMBOL: {p.symbol:10} QTY: {p.quantity:5} P&L: {pnl:6.1f}%")

if __name__ == "__main__":
    audit()
