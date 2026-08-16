import sys, os, sqlite3
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

conn = sqlite3.connect("trades.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT id, symbol, side, exit_time, pnl FROM trades")
rows = cur.fetchall()
print("All rows in trades table:")
for r in rows:
    print(dict(r))

print("\nDate test on SQLite:")
cur.execute("SELECT date('now', '-21 days')")
print("date('now', '-21 days'):", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM trades WHERE exit_time >= date('now', '-21 days')")
print("Matching count >= date('now', '-21 days'):", cur.fetchone()[0])

conn.close()
