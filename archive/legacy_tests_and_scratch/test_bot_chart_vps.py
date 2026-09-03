import sys, os
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

import database
import sqlite3
from chart_generator import generate_daily_pnl_chart

print("=== CHECK DB TRADES & DAILY_STATS IN VPS ===")
conn = sqlite3.connect("trades.db")
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM trades")
print("Trades count:", cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM daily_stats")
print("daily_stats count:", cur.fetchone()[0])
conn.close()

path = generate_daily_pnl_chart(days=0)
print("Generated chart path:", path)
if os.path.exists(path):
    print("File size:", os.path.getsize(path), "bytes")
