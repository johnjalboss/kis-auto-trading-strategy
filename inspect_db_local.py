import sqlite3
if __name__ == "__main__":
    conn = sqlite3.connect('trades.db')
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cur.fetchall()
    print("Tables:", tables)
    for t in tables:
        t_name = t[0]
        print(f"\n--- Table {t_name} ---")
        try:
            cur.execute(f"SELECT * FROM {t_name} LIMIT 10")
            print([d[0] for d in cur.description])
            for row in cur.fetchall():
                print(row)
        except Exception as e:
            print("Error:", e)
    conn.close()
