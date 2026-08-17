import subprocess
cmd = ['ssh', '-i', 'id_rsa', '-o', 'StrictHostKeyChecking=no', 'ubuntu@141.148.172.12',
       'python3', '-c', 'import sqlite3; conn=sqlite3.connect("/home/ubuntu/kis-auto-trading/trades.db"); cur=conn.cursor(); cur.execute("SELECT * FROM positions"); rows = cur.fetchall(); print("Total rows:", len(rows)); print(rows); conn.close()']
res = subprocess.run(cmd, capture_output=True, text=True)
print("VPS positions query output:", res.stdout.strip())
