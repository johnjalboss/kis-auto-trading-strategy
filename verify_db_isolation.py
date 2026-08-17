import subprocess
import sqlite3

# 1. Local DB verification
conn = sqlite3.connect('trades.db')
cur = conn.cursor()
cur.execute('SELECT COUNT(*), MAX(created_at) FROM trades')
cnt, max_date = cur.fetchone()
print(f'Local trades.db: {cnt} trades, Latest trade date: {max_date}')
conn.close()

# 2. VPS DB verification
cmd = ['ssh', '-i', 'id_rsa', '-o', 'StrictHostKeyChecking=no', 'ubuntu@141.148.172.12', 
       'python3', '-c', 'import sqlite3; conn=sqlite3.connect("/home/ubuntu/kis-auto-trading/trades.db"); cur=conn.cursor(); cur.execute("SELECT COUNT(1), MAX(created_at) FROM trades"); print("VPS trades.db:", cur.fetchone()); conn.close()']
res = subprocess.run(cmd, capture_output=True, text=True)
print(res.stdout)
