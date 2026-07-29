import sqlite3
import os

DB_PATH = "us_stocks_data.db"
if not os.path.exists(DB_PATH):
    print("DB file not found!")
    exit(1)

conn = sqlite3.connect(DB_PATH)
try:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cur.fetchall()
    print("Tables in DB:", [t[0] for t in tables])
    
    if "theme_signals" in [t[0] for t in tables]:
        cur.execute("SELECT count(*) FROM theme_signals")
        print("theme_signals count:", cur.fetchone()[0])
        
        cur.execute("SELECT * FROM theme_signals LIMIT 3")
        print("theme_signals sample:", cur.fetchall())
        
    if "theme_recommendations" in [t[0] for t in tables]:
        cur.execute("SELECT count(*) FROM theme_recommendations")
        print("theme_recommendations count:", cur.fetchone()[0])
        
        cur.execute("SELECT * FROM theme_recommendations LIMIT 3")
        print("theme_recommendations sample:", cur.fetchall())
except Exception as e:
    print("Error:", e)
finally:
    conn.close()
