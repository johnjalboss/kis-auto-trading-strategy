import sqlite3
import json

conn = sqlite3.connect('us_stocks_data.db')
cur = conn.cursor()

# Query stock_metadata sample
cur.execute("SELECT ticker, name, theme_tags FROM stock_metadata LIMIT 10")
print("Stock metadata sample:")
for row in cur.fetchall():
    print(row)

print("\n--- Finding where GEV, DELL, SMCI, CRWV, CRWD are classified ---")
for ticker in ['GEV', 'DELL', 'SMCI', 'CRWV', 'CRWD']:
    cur.execute("SELECT ticker, name, industry, theme_tags, summary FROM stock_metadata WHERE ticker = ?", (ticker,))
    row = cur.fetchone()
    if row:
        print(f"Ticker: {row[0]}")
        print(f"  Name: {row[1]}")
        print(f"  Industry: {row[2]}")
        print(f"  Themes: {row[3]}")
        print(f"  Summary[:150]: {row[4][:150] if row[4] else 'None'}")
    else:
        print(f"Ticker {ticker} not found in stock_metadata")

print("\n--- Finding all stocks mapped to nand_memory ---")
cur.execute("SELECT ticker, name, industry, theme_tags FROM stock_metadata WHERE theme_tags LIKE '%nand_memory%'")
rows = cur.fetchall()
print(f"Total nand_memory stocks found: {len(rows)}")
for row in rows:
    print(row)

conn.close()
