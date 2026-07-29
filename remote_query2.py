import sqlite3

try:
    conn = sqlite3.connect('/home/ubuntu/kis-auto-trading/server_trades.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    print("Tables:", cursor.fetchall())
except Exception as e:
    print(e)
