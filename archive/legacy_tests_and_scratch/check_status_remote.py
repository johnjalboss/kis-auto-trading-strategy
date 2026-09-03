import sqlite3
import requests
import sys
import os

db_path = '/home/ubuntu/kis-auto-trading/trades.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('SELECT symbol FROM positions')
symbols = [row['symbol'] for row in cur.fetchall()]
conn.close()

print(f"SYMBOLS: {symbols}")
print(f"COUNT: {len(symbols)}")

# Check bot.log for macro
log_path = '/home/ubuntu/kis-auto-trading/bot.log'
if os.path.exists(log_path):
    print("Recent Macro Analysis:")
    os.system(f"grep -a 'Macro score' {log_path} | tail -n 5")
    os.system(f"grep -a 'Sentiment score' {log_path} | tail -n 5")
    os.system(f"grep -a 'BUYING_POWER' {log_path} | tail -n 5")
