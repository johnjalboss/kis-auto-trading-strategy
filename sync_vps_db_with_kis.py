"""
Sync SQLite trades.db positions table with live KIS Broker API
Removes ghost positions (e.g. GIS) that were sold in KIS but left in DB.
"""
import sys, os, sqlite3
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

from trader import Trader

t = Trader()
kis_pos = t.get_positions()
live_symbols = {p.symbol for p in kis_pos}

print("==========================================================")
print("🧹 SYNCING DB POSITIONS WITH LIVE KIS BROKER API")
print("==========================================================")
print(f"Live KIS Symbols ({len(live_symbols)}): {live_symbols}")

conn = sqlite3.connect("trades.db")
cur = conn.cursor()
cur.execute("SELECT symbol FROM positions")
db_symbols = [r[0] for r in cur.fetchall()]
print(f"Current DB Symbols ({len(db_symbols)}): {db_symbols}")

removed = 0
for sym in db_symbols:
    if sym not in live_symbols:
        cur.execute("DELETE FROM positions WHERE symbol = ?", (sym,))
        print(f"🗑️ Removed stale ghost position from DB: {sym}")
        removed += 1

conn.commit()
conn.close()

print(f"\n✅ Sync complete! Removed {removed} ghost positions.")
print("==========================================================")
