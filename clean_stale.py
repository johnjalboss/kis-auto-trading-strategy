import sqlite3

def main():
    db_path = "/home/ubuntu/kis-auto-trading/trades.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM positions WHERE symbol = 'DELL'")
    conn.commit()
    print("Deleted DELL from positions:", cursor.rowcount, "rows affected.")
    conn.close()

if __name__ == "__main__":
    main()
