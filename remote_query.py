import sqlite3
import pandas as pd

try:
    conn = sqlite3.connect('/home/ubuntu/kis-auto-trading/server_trades.db')
    print("=== ACTIVE ===")
    print(pd.read_sql("SELECT * FROM active_positions WHERE symbol='MRVL'", conn))
    print("=== HISTORY ===")
    print(pd.read_sql("SELECT * FROM trade_history WHERE symbol='MRVL' ORDER BY timestamp DESC LIMIT 20", conn))
except Exception as e:
    print(e)
