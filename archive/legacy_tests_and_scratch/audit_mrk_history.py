import sqlite3

conn = sqlite3.connect("trades.db")
cur = conn.cursor()

print("=== ALL MRK TRADES IN TRADES.DB ===")
for r in cur.execute("SELECT id, symbol, side, quantity, price, pnl, pnl_pct, reason, regime, created_at FROM trades WHERE symbol='MRK' ORDER BY id ASC"):
    print(r)

print("\n=== RECENT TRADES IN AUGUST 2026 ===")
for r in cur.execute("SELECT id, symbol, side, quantity, price, pnl, reason, regime, created_at FROM trades WHERE date(created_at) >= '2026-08-01' ORDER BY id ASC"):
    print(r)
