import sqlite3
import json
import os

db_path = "/home/ubuntu/kis-auto-trading/trades.db"

def get_trades():
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found")
        return []
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get schema just in case
        cursor.execute("PRAGMA table_info(trades)")
        columns = [col[1] for col in cursor.fetchall()]
        
        query = "SELECT * FROM trades WHERE symbol IN ('MRVL', 'DAWN') AND timestamp >= '2026-03-05' ORDER BY timestamp ASC"
        cursor.execute(query)
        rows = cursor.fetchall()
        
        trades = []
        for row in rows:
            trade = dict(zip(columns, row))
            trades.append(trade)
        
        return trades
    except Exception as e:
        print(f"Error querying database: {e}")
        return []
    finally:
        conn.close()

if __name__ == "__main__":
    trades = get_trades()
    print(json.dumps(trades, indent=2))
