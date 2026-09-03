import sqlite3, sys
sys.path.append('/home/ubuntu/kis-auto-trading')

# DB 포지션 확인
db = sqlite3.connect('/home/ubuntu/kis-auto-trading/trades.db')
db.row_factory = sqlite3.Row
cur = db.cursor()
rows = cur.execute('SELECT * FROM positions').fetchall()
print("=== DB 내 positions ===")
for r in rows:
    d = dict(r)
    print(f"  {d}")

# KIS 실제 보유 종목 확인
import trader
t = trader.get_trader()
t.start()
import requests
print("\n=== KIS 실제 보유 종목 (NASD/NYS/AMS) ===")
for ex in ['NASD', 'NYS', 'AMS']:
    url = f'{t.base_url}/uapi/overseas-stock/v1/trading/inquire-balance'
    tr_id = 'VTTS3012R' if t.is_paper else 'TTTS3012R'
    params = {'CANO': t.account_no, 'ACNT_PRDT_CD': t.account_cd, 'OVRS_EXCG_CD': ex, 'TR_CRCY_CD': 'USD', 'CTX_AREA_FK200': '', 'CTX_AREA_NK200': ''}
    resp = requests.get(url, headers=t._get_headers(tr_id), params=params)
    data = resp.json()
    if data.get('rt_cd') == '0':
        for item in data.get('output1', []):
            qty = int(item.get('ovrs_cblc_qty', 0))
            if qty > 0:
                print(f"  {ex}: {item.get('ovrs_pdno')} qty={qty} sellable={item.get('ord_psbl_qty')} avg={item.get('pchs_avg_pric')}")
