import sys
sys.path.append('/home/ubuntu/kis-auto-trading')

import trader
import time

t = trader.get_trader()
t.start()

positions = t.get_positions()
target_price = 0
for p in positions:
    if p.symbol == 'HST':
        target_price = p.current_price
        print(f"Found HST in portfolio. Current price from portfolio: {target_price}")
        break

if target_price > 0:
    print(f"Submitting sell order at EXACT portfolio price: {target_price}")
    result = t.sell('HST', 1, target_price)
    print(f"Sell result: {result}")
else:
    print("HST not found in portfolio or price is 0.")

time.sleep(2)
print("Remaining positions:")
for p in t.get_positions():
    print(p)
