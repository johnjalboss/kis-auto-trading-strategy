import sys
sys.path.append('/home/ubuntu/kis-auto-trading')

import trader
import requests
t = trader.get_trader()
t.start()

# Raw API call to sell via Limit Order with exactly matching tick size
price = t.get_price('HST')
# round to 2 decimals
rounded_price = round(price - 0.05, 2) # slightly lower to ensure execution
print(f"HST current price: {price}, using limit price: {rounded_price:.2f}")

url = f'{t.base_url}/uapi/overseas-stock/v1/trading/order'
tr_id = 'VTTT1001U' if t.is_paper else 'TTTT1006U'

body = {
    "CANO": t.account_no,
    "ACNT_PRDT_CD": t.account_cd,
    "OVRS_EXCG_CD": "NASD",
    "PDNO": "HST",
    "ORD_QTY": "1",
    "OVRS_ORD_UNPR": f"{rounded_price:.2f}",
    "SLL_TYPE": "00",
    "ORD_SVR_DVSN_CD": "0",
    "ORD_DVSN": "00"
}

resp = requests.post(url, headers=t._get_headers(tr_id), json=body)
print(f"Sell API response: {resp.json()}")

import time
time.sleep(2)
# Check positions remaining
positions = t.get_positions()
for p in positions:
    print(p)
