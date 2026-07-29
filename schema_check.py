import sqlite3, os
os.chdir('/home/ubuntu/kis-auto-trading')
db = sqlite3.connect('trades.db')
db.row_factory = sqlite3.Row

# Schema check
cols = [d[1] for d in db.execute('PRAGMA table_info(trades)').fetchall()]
print("Schema:", cols)

# Dynamic analysis based on actual columns
rows_all = db.execute("SELECT * FROM trades LIMIT 3").fetchall()
for r in rows_all:
    print(dict(r))
