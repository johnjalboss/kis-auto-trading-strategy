import sqlite3
conn = sqlite3.connect('us_stocks_data.db')
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM stock_metadata")
total = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM stock_metadata WHERE theme_tags != '' AND theme_tags IS NOT NULL")
classified = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM stock_metadata WHERE theme_tags = '' OR theme_tags IS NULL")
unclassified = cur.fetchone()[0]
print(f"Total: {total}")
print(f"Classified: {classified} ({classified/total*100:.1f}%)")
print(f"Unclassified: {unclassified}")
conn.close()
