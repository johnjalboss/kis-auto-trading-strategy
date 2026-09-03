import sqlite3
import os

db_path = os.path.expanduser('~/kis-auto-trading/trades.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute('SELECT id, symbol, quantity, price, total, pnl, exit_time FROM trades WHERE side="SELL" ORDER BY exit_time DESC LIMIT 10;')
rows = cur.fetchall()
if not rows:
    print('No SELL rows found.')
else:
    for r in rows:
        d = dict(r)
        print(d)
