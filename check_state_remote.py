import sys
from trader import Trader
from strategy import StrategyEngine

try:
    t = Trader()
    se = StrategyEngine()
    pos = t.get_positions()
    bp = t.get_buying_power()
    print("=== VPS ACTIVE STATE ===")
    print(f"Buying Power: ${bp:,.2f}")
    print(f"Open Positions Count: {len(pos)}")
    for p in pos:
         print(f"  {p.symbol}: qty={p.quantity}, avg={p.avg_price}, current={p.current_price}, market_value=${p.market_value:,.2f}")
except Exception as e:
    print("Error querying state:", e)
