import sqlite3
from datetime import datetime, timedelta

dbs = ['trades.db', 'server_trades.db', 'trading.db', 'trade_journal.db']

all_trades = []
best_db = None

for db in dbs:
    try:
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print("DB: {} | Tables: {}".format(db, tables))
        
        for tbl in tables:
            cols = [c[1] for c in cur.execute("PRAGMA table_info({})".format(tbl)).fetchall()]
            print("  {}: {}".format(tbl, cols))
            try:
                count = cur.execute("SELECT COUNT(*) FROM {}".format(tbl)).fetchone()[0]
                print("    rows:", count)
            except Exception as err:
                print("⚠️ [check_db.py] Fallback triggered:", err)
        conn.close()
    except Exception as e:
        print("Error {}: {}".format(db, e))

print("\n\n=== 거래 데이터 분석 ===")
# Try most likely DB/table combinations
for db, tbl in [('trades.db','trades'), ('server_trades.db','trades'), 
                 ('server_trades.db','positions'), ('trading.db','trades'),
                 ('trading.db','positions'), ('trade_journal.db','entries')]:
    try:
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM {} LIMIT 1".format(tbl))
        row = cur.fetchone()
        if row:
            print("Found data in {}.{}:".format(db, tbl))
            print("  Columns:", list(row.keys()))
            cur.execute("SELECT COUNT(*) FROM {}".format(tbl))
            print("  Total rows:", cur.fetchone()[0])
        conn.close()
    except Exception as err:
        print("⚠️ [check_db.py] Fallback triggered:", err)
