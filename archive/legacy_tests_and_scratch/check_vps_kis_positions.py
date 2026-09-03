import sys, os
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

from trader import Trader
import database

t = Trader()
db = database.get_database()

print("==========================================================")
print("🔍 LIVE KIS BROKER API POSITIONS AUDIT")
print("==========================================================")

# 1. KIS API Direct Query
try:
    kis_pos = t.get_positions()
    print(f"1. KIS API Live Positions Count: {len(kis_pos)}")
    for p in kis_pos:
        print(f"   - {p.symbol}: Qty {p.quantity}, Avg ${p.avg_price:.2f}, Curr ${p.current_price:.2f}")
except Exception as e:
    print("KIS API query error:", e)

# 2. SQLite DB positions table
db_pos = db.get_open_positions()
print(f"\n2. trades.db DB Positions Count: {len(db_pos)}")
for p in db_pos:
    print(f"   - {p['symbol']}: Qty {p['quantity']}, Avg ${p['avg_price']:.2f}")

print("==========================================================")
