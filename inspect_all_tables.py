import sqlite3

conn = sqlite3.connect("trades.db")
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print("Tables in trades.db:", tables)

for t in tables:
    t_name = t[0]
    cur.execute(f"SELECT COUNT(*) FROM {t_name}")
    count = cur.fetchone()[0]
    print(f"Table '{t_name}': {count} rows")
    if count > 0:
        cur.execute(f"SELECT * FROM {t_name} LIMIT 3")
        print(f"   Sample: {cur.fetchall()}")

conn.close()
