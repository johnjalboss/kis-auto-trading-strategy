import sqlite3
import os

def read_db():
    db_path = "/home/ubuntu/kis-auto-trading/trades.db"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=== TRADE HISTORY (LAST 20) ===")
    try:
        cursor.execute("SELECT * FROM trade_history ORDER BY id DESC LIMIT 20")
        rows = cursor.fetchall()
        for r in rows:
            print(r)
    except Exception as e:
        print(f"Error reading trade_history: {e}")
        
    print("\n=== RECENT SIGNALS (IF TABLE EXISTS) ===")
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='signals'")
        if cursor.fetchone():
            cursor.execute("SELECT * FROM signals ORDER BY id DESC LIMIT 5")
            rows = cursor.fetchall()
            for r in rows:
                print(r)
    except:
        pass
        
    conn.close()

if __name__ == "__main__":
    read_db()
