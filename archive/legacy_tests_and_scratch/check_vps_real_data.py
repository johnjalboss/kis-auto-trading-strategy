import subprocess, sys

script = """
import sqlite3
import glob
import json

print('=== DB FILES ON VPS ===')
print(glob.glob('/home/ubuntu/kis-auto-trading/*.db'))

for db_path in ['/home/ubuntu/kis-auto-trading/trades.db', '/home/ubuntu/kis-auto-trading/server_trades.db', '/home/ubuntu/kis-auto-trading/trade_journal.db']:
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        print(f'=== DB: {db_path} ===')
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in c.fetchall()]
        print('Tables:', tables)
        for t in tables:
            c.execute(f'SELECT COUNT(*) FROM {t}')
            cnt = c.fetchone()[0]
            print(f'  Table {t}: {cnt} rows')
            if 'pos' in t.lower():
                c.execute(f'SELECT * FROM {t}')
                rows = c.fetchall()
                print('    Rows:')
                for r in rows:
                    print('     ', r)
            elif 'stat' in t.lower():
                c.execute(f'SELECT * FROM {t} ORDER BY rowid DESC LIMIT 10')
                rows = c.fetchall()
                print('    Recent stats:')
                for r in rows:
                    print('     ', r)
            elif 'trade' in t.lower():
                c.execute(f'SELECT * FROM {t} ORDER BY rowid DESC LIMIT 10')
                rows = c.fetchall()
                print('    Recent trades:')
                for r in rows:
                    print('     ', r)
    except Exception as e:
        print(f'Error with {db_path}: {e}')
"""

res = subprocess.run(
    ['ssh', '-i', 'id_rsa', '-o', 'StrictHostKeyChecking=no', 'ubuntu@141.148.172.12', 'python3'],
    input=script,
    capture_output=True,
    text=True,
    encoding='utf-8',
    errors='replace'
)

with open('vps_db_dump.txt', 'w', encoding='utf-8') as f:
    f.write('STDOUT:\n' + res.stdout + '\nSTDERR:\n' + res.stderr)

print("Saved to vps_db_dump.txt successfully")
