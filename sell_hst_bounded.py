import sys
sys.path.append('/home/ubuntu/kis-auto-trading')

import trader
import time

t = trader.get_trader()
t.start()

price = t.get_price('HST')
print(f"Current raw price: {price}")
# strictly use the price without subtracting too much so we don't hit the lower bound
safe_limit_price = round(price, 2)
print(f"Submitting native sell at exact current limit price: {safe_limit_price}")

result = t.sell('HST', 1, safe_limit_price)
print(f"Native Sell Result: {result}")

time.sleep(2)
positions = t.get_positions()
print("Remaining Positions:")
for p in positions:
    print(p)
