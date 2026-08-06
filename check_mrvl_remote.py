import sqlite3
import json
import os

db_path = '/home/ubuntu/kis-auto-trading/trades.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM trades WHERE symbol = 'MRVL' ORDER BY id DESC LIMIT 10")
    rows = cursor.fetchall()
    print("--- Trades DB ---")
    for row in rows:
        d = dict(row)
        if d['id'] >= 20:
            print(f"ID:{d['id']} Side:{d['side']} Price:{d['price']} Qty:{d['quantity']} Time:{d['entry_time'] or d['exit_time']} Reason:{d.get('reason', 'N/A')} Regime:{d.get('regime', 'N/A')}")
    conn.close()

log_dir = '/home/ubuntu/kis-auto-trading/logs/'
print("\n--- Recent MRVL Log Entries ---")
if os.path.exists(log_dir):
    log_files = sorted([os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith('.log')], key=os.path.getmtime, reverse=True)
    for log_file in log_files[:2]: # Check most recent 2 logs
        print(f"Scanning {log_file}...")
        with open(log_file, 'r', errors='ignore') as f:
            lines = f.readlines()
            for line in lines:
                if 'MRVL' in line and ('score' in line.lower() or 'signal' in line.lower() or 'trade' in line.lower() or 'buy' in line.lower().split() or 'execute' in line.lower()):
                    print(line.strip())
