import sqlite3
import pandas as pd

if __name__ == "__main__":
    conn = sqlite3.connect("trades.db")
    df = pd.read_sql_query("SELECT * FROM trades", conn)

    print("SQQQ Trades:")
    print(df[df['symbol'] == 'SQQQ'].tail(5))

    print("\nTQQQ Trades:")
    print(df[df['symbol'] == 'TQQQ'].tail(5))
