import sqlite3, os

db_file = "trades.db"
if os.path.exists(db_file):
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print("Local DB Tables:", tables)
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        cnt = cur.fetchone()[0]
        print(f"  Local Table '{t}': {cnt} rows")
        if cnt > 0 and t == "trades":
            cur.execute(f"SELECT * FROM {t} LIMIT 5")
            print("  Sample local trades:", cur.fetchall())
    conn.close()
