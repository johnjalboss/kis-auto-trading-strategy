import sqlite3, os, sys
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

conn = sqlite3.connect("trades.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM trades")
print("Total rows in trades table:", cur.fetchone()[0])

cur.execute("SELECT id, symbol, side, exit_time, created_at, pnl FROM trades")
rows = cur.fetchall()
print("\nAll trade rows in trades.db:")
for r in rows:
    print(dict(r))

conn.close()
