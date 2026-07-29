import sqlite3, sys
sys.path.append('/home/ubuntu/kis-auto-trading')

db = sqlite3.connect('/home/ubuntu/kis-auto-trading/trades.db')
cur = db.cursor()

# DB에서 사용자 수동 매도로 인해 사라진 HST 삭제
cur.execute("DELETE FROM positions WHERE symbol = 'HST'")
db.commit()

rows_after = cur.execute('SELECT symbol FROM positions').fetchall()
print(f"DB 동기화 완료. 현재 잔고 positions: {[r[0] for r in rows_after]}")
db.close()
