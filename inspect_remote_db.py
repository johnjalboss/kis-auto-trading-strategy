import sqlite3
import pandas as pd
import sys

db_path = '/home/ubuntu/kis-auto-trading/trades.db'

def get_schema(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tables: {tables}")
    for table_name in [t[0] for t in tables]:
        print(f"\nSchema for {table_name}:")
        cursor.execute(f"PRAGMA table_info({table_name});")
        print(cursor.fetchall())

try:
    conn = sqlite3.connect(db_path)
    get_schema(conn)
    
    # Try common table names or search
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%trade%';")
    trade_tables = cursor.fetchall()
    
    for (table,) in trade_tables:
        print(f"\n--- Data from {table} (MRVL) ---")
        try:
            # Check if 'symbol' or 'ticker' column exists
            cursor.execute(f"PRAGMA table_info({table});")
            cols = [c[1] for c in cursor.fetchall()]
            sym_col = 'symbol' if 'symbol' in cols else ('ticker' if 'ticker' in cols else None)
            
            if sym_col:
                df = pd.read_sql(f"SELECT * FROM {table} WHERE {sym_col}='MRVL'", conn)
                print(df)
            else:
                print(f"No symbol column found in {table}. Columns: {cols}")
        except Exception as e:
            print(f"Error querying {table}: {e}")

except Exception as e:
    print(f"Global Error: {e}")
finally:
    if 'conn' in locals():
        conn.close()
