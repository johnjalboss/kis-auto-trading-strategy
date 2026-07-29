import sqlite3
import os

def check_db():
    db_path = "/home/ubuntu/kis-auto-trading/trades.db"
    if not os.path.exists(db_path):
        print(f"DATABASE NOT FOUND: {db_path}")
        return
        
    print(f"File size: {os.path.getsize(db_path)} bytes")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # List all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"Tables: {tables}")
    
    for table_name in [t[0] for t in tables]:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f" - Table {table_name}: {count} rows")
        
        if count > 0:
            print(f"   Sample from {table_name}:")
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
            print(f"   {cursor.fetchall()}")
            
    conn.close()

if __name__ == "__main__":
    check_db()
