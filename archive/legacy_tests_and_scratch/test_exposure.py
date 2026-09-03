import time
from dotenv import load_dotenv
load_dotenv()

from trader import Trader
from strategy import StrategyEngine
import sys
from loguru import logger
logger.remove()
logger.add(sys.stderr, level="ERROR")

from database import get_database

t = Trader()
time.sleep(1)
se = StrategyEngine()
se.sync_positions(t.get_positions())

positions = se.get_all_positions()
bp = t.get_buying_power()
total_value = bp

print(f"BP: {bp}")
print("Positions:", positions)

pos_values = {}
for sym, pos in positions.items():
    price = t.get_price(sym)
    if price > 0:
        val = price * pos.quantity
        pos_values[sym] = (val, price, pos.quantity)
        total_value += val
        
print(f"Total Value: {total_value}")
if total_value > 0:
    current_exposure = (total_value - bp) / total_value
    print(f"Current Exposure: {current_exposure:.2%}")
    target = 0.5
    print(f"Target Exposure: {target:.2%}")
    if current_exposure > target + 0.05:
        excess = 1.0 - (target / current_exposure)
        print(f"TRIGGER: Excess ratio {excess:.2%}")
        for sym, (val, price, qty) in pos_values.items():
            sell_qty = max(1, int(qty * excess))
            print(f"WOULD SELL: {sell_qty} of {sym} (current {qty})")
    else:
        print("NO TRIGGER")
