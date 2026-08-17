import sqlite3

conn = sqlite3.connect('trades.db')
cur = conn.cursor()
cur.execute("SELECT * FROM positions")
rows = cur.fetchall()
print(f"COUNT: {len(rows)}")
for r in rows:
    print(r)
conn.close()
