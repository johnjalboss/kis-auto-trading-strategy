#!/usr/bin/env python3
import sys, os
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')
import sqlite3

conn = sqlite3.connect('trades.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 테이블 목록
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("테이블 목록:", tables)

# 각 테이블 스키마
for t in tables:
    cols = [(r[1], r[2]) for r in cur.execute(f"PRAGMA table_info({t})").fetchall()]
    print(f"\n[{t}] 컬럼:", cols)
    rows = cur.execute(f"SELECT * FROM {t} ORDER BY rowid DESC LIMIT 5").fetchall()
    for r in rows:
        print(" ", dict(r))

conn.close()
