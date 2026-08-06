import sqlite3
import os

db_path = "/home/ubuntu/kis-auto-trading/trades.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT symbol, side, quantity, price, created_at, reason FROM trades WHERE symbol='ALRM'")
    rows = cur.fetchall()
    print("=== ALRM TRADES ===")
    for r in rows:
        print(f"Symbol: {r[0]}, Side: {r[1]}, Qty: {r[2]}, Price: {r[3]}, Time: {r[4]}, Reason: {r[5]}")
else:
    print("Database not found on VPS")
