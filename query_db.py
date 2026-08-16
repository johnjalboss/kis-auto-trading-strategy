import sqlite3

conn = sqlite3.connect("trades.db")
cur = conn.cursor()

print("=== TABLES ===")
for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'"):
    print(r)

print("\n=== DAILY REPORTS LOCK TABLE ===")
try:
    for row in cur.execute("SELECT * FROM daily_reports ORDER BY id DESC LIMIT 15"):
        print(row)
except Exception as e:
    print("daily_reports err:", e)

print("\n=== RECENT TRADES ===")
try:
    for row in cur.execute("SELECT id, symbol, side, quantity, price, pnl, created_at FROM trades ORDER BY id DESC LIMIT 10"):
        print(row)
except Exception as e:
    print("trades err:", e)

print("\n=== POSITIONS ===")
try:
    for row in cur.execute("SELECT symbol, quantity, entry_price, current_price, pnl_pct FROM positions"):
        print(row)
except Exception as e:
    print("positions err:", e)
