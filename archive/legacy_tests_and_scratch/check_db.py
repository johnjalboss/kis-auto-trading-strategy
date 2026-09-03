import sqlite3, os

db_path = "/home/ubuntu/kis-auto-trading/trades.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    print("=== TABLES ===")
    for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        print(row)
    print("\n=== POSITIONS ===")
    for row in cur.execute("SELECT * FROM positions"):
        print(row)
    print("\n=== RECENT TRADES ===")
    for row in cur.execute("SELECT * FROM trades ORDER BY id DESC LIMIT 5"):
        print(row)
    conn.close()
else:
    print("trades.db does not exist")
