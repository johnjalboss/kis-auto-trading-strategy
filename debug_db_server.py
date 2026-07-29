import sqlite3
import os

def check():
    db = "trades.db"
    if not os.path.exists(db):
        print(f"Error: {db} not found")
        return
        
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    print("--- DATES ---")
    cur.execute("SELECT DISTINCT date(exit_time, '-14 hours') as d FROM trades WHERE side='SELL' ORDER BY d DESC LIMIT 15")
    for r in cur.fetchall():
        print(r['d'])
    
    print("--- RECENT STATS ---")
    cur.execute("SELECT date(exit_time, '-14 hours') as d, sum(pnl) as p FROM trades WHERE side='SELL' GROUP BY d ORDER BY d DESC LIMIT 5")
    for r in cur.fetchall():
        print(f"{r['d']}: {r['p']}")
        
    conn.close()

if __name__ == "__main__":
    check()
