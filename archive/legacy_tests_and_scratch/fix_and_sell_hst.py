import sqlite3, sys
sys.path.append('/home/ubuntu/kis-auto-trading')

db = sqlite3.connect('/home/ubuntu/kis-auto-trading/trades.db')
cur = db.cursor()

# DB에서 SQQQ 포지션 삭제 (실제로 보유하지 않음)
rows_before = cur.execute('SELECT symbol FROM positions').fetchall()
print(f"삭제 전 positions: {[r[0] for r in rows_before]}")

cur.execute("DELETE FROM positions WHERE symbol = 'SQQQ'")
db.commit()

rows_after = cur.execute('SELECT symbol FROM positions').fetchall()
print(f"삭제 후 positions: {[r[0] for r in rows_after]}")
db.close()

# HST 즉시 매도 실행
import trader
t = trader.get_trader()
t.start()

print("\n=== HST 즉시 매도 시도 ===")
import requests

# KIS 해외주식 시장가 매도
url = f'{t.base_url}/uapi/overseas-stock/v1/trading/order'
tr_id = 'VTTT1002U' if t.is_paper else 'TTTT1002U'
body = {
    'CANO': t.account_no,
    'ACNT_PRDT_CD': t.account_cd,
    'OVRS_EXCG_CD': 'NASD',
    'PDNO': 'HST',
    'ORD_DVSN': '00',  # 지정가
    'ORD_QTY': '1',
    'OVRS_ORD_UNPR': '0',  # 시장가는 0
    'ORD_SVR_DVSN_CD': '0',
    'SLL_TYPE': 'F',
}
# 실제로는 t.place_order 같은 기존 메서드 사용
try:
    result = t.sell('HST', 1, 0)  # 시장가 매도
    print(f"매도 결과: {result}")
except Exception as e:
    print(f"직접 매도 오류: {e}")
    # 대안: 최신 가격으로 지정가 매도
    try:
        price = t.get_price('HST')
        print(f"HST 현재가: {price}")
        result = t.sell('HST', 1, price)
        print(f"지정가 매도 결과: {result}")
    except Exception as e2:
        print(f"지정가 매도도 오류: {e2}")
