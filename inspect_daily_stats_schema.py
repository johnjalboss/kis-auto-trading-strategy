import sqlite3, os

db_path = "trades.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(daily_stats)")
    print("daily_stats columns:", cur.fetchall())
    
    cur.execute("SELECT * FROM daily_stats ORDER BY date DESC LIMIT 10")
    print("\ndaily_stats last 10 rows:")
    for r in cur.fetchall():
        print(r)
    conn.close()
