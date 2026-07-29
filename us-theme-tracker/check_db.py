import sqlite3
conn = sqlite3.connect('us_stocks_data.db')
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM stock_metadata WHERE summary IS NOT NULL AND summary != 'FETCH_FAILED'")
print('Has summary:', cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM stock_metadata WHERE industry IS NOT NULL AND industry != ''")
print('Has industry:', cur.fetchone()[0])

cur.execute("SELECT industry, COUNT(*) as cnt FROM stock_metadata WHERE industry IS NOT NULL AND industry != '' GROUP BY industry ORDER BY cnt DESC")
rows = cur.fetchall()
print(f'\nTotal distinct industries: {len(rows)}')
for ind, cnt in rows:
    print(f'  {cnt:4d}  {ind}')

conn.close()
