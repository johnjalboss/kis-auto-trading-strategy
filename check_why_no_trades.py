import sys, os
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

import database
import config
from trader import Trader

db = database.get_database()
t = Trader()

positions = db.get_open_positions()
bp = t.get_buying_power()
max_pos = getattr(config, 'MAX_POSITIONS', 3)

print("==========================================================")
print("🔍 WHY NO TRADES DIAGNOSIS")
print("==========================================================")
print(f"1. Cash Buying Power: ${bp:.2f}")
print(f"2. Open Positions Count: {len(positions)} / {max_pos} Max Positions")
for p in positions:
    print(f"   - {p['symbol']}: Qty {p['quantity']}, Avg ${p['avg_price']:.2f}")

if len(positions) >= max_pos:
    print("\n💡 REASON: Max position limit reached! (3/3 slots full).")
    print("   The bot will only buy if an existing position is sold or upgraded.")
elif bp < 100:
    print("\n💡 REASON: Insufficient buying power cash.")
else:
    print("\n💡 REASON: Active screening underway, waiting for high confidence setup (score >= 80).")
print("==========================================================")
