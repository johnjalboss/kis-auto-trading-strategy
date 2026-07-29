import sys
sys.path.append('/home/ubuntu/kis-auto-trading')

import trader
import time

t = trader.get_trader()
t.start()

# Let's try to sell using the bot's native sell function, with a very safe explicitly float rounded price
price = t.get_price('HST')
print(f"Current raw price: {price}")
# round to safe .00 or .50 tick just in case there's some bizarre tick sizing issue
# e.g., 18.825 -> 18.80
safe_limit_price = round(price - 0.10, 1) # e.g., 18.7
print(f"Submitting native sell at limit price: {safe_limit_price}")

result = t.sell('HST', 1, safe_limit_price)
print(f"Native Sell Result: {result}")

time.sleep(2)
positions = t.get_positions()
print("Remaining Positions:")
for p in positions:
    print(p)
