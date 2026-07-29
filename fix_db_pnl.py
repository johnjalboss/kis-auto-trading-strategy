import sqlite3
import os

db_path = os.path.expanduser('~/kis-auto-trading/trades.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Find all SELL trades with 0 pnl
cur.execute('SELECT id, symbol, quantity, price, exit_time FROM trades WHERE side="SELL" AND pnl=0')
sells = cur.fetchall()

updates = 0
for sell in sells:
    sell_id = sell['id']
    symbol = sell['symbol']
    qty = sell['quantity']
    sell_price = sell['price']
    exit_time = sell['exit_time']
    
    # Find the most recent BUY before this SELL
    cur.execute('''
        SELECT price FROM trades 
        WHERE side="BUY" AND symbol=? AND entry_time <= ? 
        ORDER BY entry_time DESC LIMIT 1
    ''', (symbol, exit_time))
    
    buy = cur.fetchone()
    if buy:
        entry_price = buy['price']
        
        # Recalculate PNL
        pnl = (sell_price - entry_price) * qty
        pnl_pct = (sell_price - entry_price) / entry_price if entry_price > 0 else 0
        
        # Update DB
        cur.execute('UPDATE trades SET pnl=?, pnl_pct=? WHERE id=?', (pnl, pnl_pct, sell_id))
        updates += 1
        print(f"Fixed {symbol}: Buy @ {entry_price:.2f}, Sell @ {sell_price:.2f} -> PNL: {pnl:.2f}")

conn.commit()
conn.close()
print(f"Successfully fixed {updates} historical SELL records!")
