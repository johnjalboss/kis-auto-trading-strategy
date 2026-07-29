import sqlite3
import pandas as pd

if __name__ == "__main__":
    conn = sqlite3.connect('trades.db')
    query = "SELECT * FROM trades WHERE symbol = 'PLTD' ORDER BY id DESC LIMIT 5"
    df = pd.read_sql_query(query, conn)
    print("PLTD Trades:")
    # Print transposed for readability
    print(df.T)
