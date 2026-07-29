import sqlite3
import pandas as pd

try:
    conn = sqlite3.connect('/home/ubuntu/kis-auto-trading/trades.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    print("Tables:", cursor.fetchall())
    
    print("\n--- trades ---")
    print(pd.read_sql("SELECT * FROM trades WHERE symbol='MRVL' ORDER BY timestamp DESC LIMIT 10", conn))
    
    print("\n--- daily_performance ---")
    print(pd.read_sql("SELECT * FROM daily_performance ORDER BY date DESC LIMIT 5", conn))
except Exception as e:
    print("Error:", e)
