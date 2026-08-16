import sqlite3

conn = sqlite3.connect("trades.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT MIN(date(exit_time, '-14 hours')) as min_date, MAX(date(exit_time, '-14 hours')) as max_date FROM trades WHERE side = 'SELL'")
r = cur.fetchone()
print("Query result min_date:", r['min_date'], "max_date:", r['max_date'])

cur.execute("SELECT id, symbol, side, exit_time, pnl FROM trades")
print("\nAll trades in DB:")
for row in cur.fetchall():
    print(dict(row))

conn.close()
