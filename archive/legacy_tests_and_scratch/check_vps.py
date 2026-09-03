import sqlite3
conn = sqlite3.connect('/home/ubuntu/kis-auto-trading/trades.db')
cur = conn.cursor()
print('=== POSITIONS TABLE ===')
cur.execute('SELECT * FROM positions')
for row in cur.fetchall():
    print(row)

print('\n=== RECENT 10 TRADES ===')
cur.execute('SELECT id, symbol, side, price, quantity, pnl, created_at, reason FROM trades ORDER BY id DESC LIMIT 10')
for row in cur.fetchall():
    print(row)
conn.close()