import sqlite3

def get_recent_sells():
    try:
        conn = sqlite3.connect("server_trades.db")
        cur = conn.cursor()
        
        cur.execute("PRAGMA table_info(trades)")
        cols = [col[1] for col in cur.fetchall()]
        print("Columns:", cols)
        
        cur.execute("SELECT * FROM trades WHERE action='SELL' ORDER BY id DESC LIMIT 15")
        rows = cur.fetchall()
        
        print("\nRecent SELL trades:")
        for r in rows:
            print(dict(zip(cols, r)))
            
        conn.close()
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    get_recent_sells()
