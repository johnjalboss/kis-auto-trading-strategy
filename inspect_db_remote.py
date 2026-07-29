import sqlite3
import os

if __name__ == "__main__":
    db_path = "/home/ubuntu/kis-auto-trading/trades.db"
    if not os.path.exists(db_path):
        print("Error: DB file not found")
        exit(1)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Get table names
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cur.fetchall()]
    print("Tables on VM:", tables)

    for t in tables:
        print(f"\n=== Table {t} (Recent 15 Rows) ===")
        try:
            cur.execute(f"PRAGMA table_info({t})")
            cols = [c[1] for c in cur.fetchall()]
            print("Columns:", cols)
            
            cur.execute(f"SELECT * FROM {t} ORDER BY rowid DESC LIMIT 15")
            rows = cur.fetchall()
            for r in rows:
                print(r)
        except Exception as e:
            print("Error:", e)

    conn.close()
