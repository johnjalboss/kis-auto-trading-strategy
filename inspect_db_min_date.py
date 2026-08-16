import sqlite3, os

conn = sqlite3.connect("trades.db")
cur = conn.cursor()
cur.execute("SELECT MIN(entry_time), MIN(exit_time), MAX(entry_time), MAX(exit_time) FROM trades")
print("Trades date bounds:", cur.fetchall())

cur.execute("SELECT MIN(date), MAX(date) FROM daily_stats")
print("daily_stats date bounds:", cur.fetchall())

conn.close()
