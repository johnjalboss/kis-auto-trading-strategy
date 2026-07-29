import sys
sys.path.append('/home/ubuntu/kis-auto-trading')

import trader
import requests
import time
import math
t = trader.get_trader()
t.start()

symbol = 'HST'
exchange = 'NASD'
tr_id = "HHDFS00000300"
url = f"{t.base_url}/uapi/overseas-price/v1/quotations/price"

params = {"AUTH": "", "EXCD": exchange, "SYMB": symbol}

try:
    resp = requests.get(url, headers=t._get_headers(tr_id), params=params)
    data = resp.json()
except Exception as e:
    print(e)

price_str = data.get("output", {}).get("last", "0")
price_float = float(price_str)

# Ensure strictly 2 decimal places e.g., 18.825 -> 18.82 (round down for sell to ensure execution)
rounded_price = math.floor(price_float * 100) / 100.0
final_price_str = f"{rounded_price:.2f}"
print(f"Original API price: {price_str}, Float: {price_float}, Rounded for Limit: {final_price_str}")

url_order = f'{t.base_url}/uapi/overseas-stock/v1/trading/order'
tr_id_order = 'VTTT1001U' if t.is_paper else 'TTTT1006U'

body = {
    "CANO": t.account_no,
    "ACNT_PRDT_CD": t.account_cd,
    "OVRS_EXCG_CD": exchange,
    "PDNO": symbol,
    "ORD_QTY": "1",
    "OVRS_ORD_UNPR": final_price_str,
    "SLL_TYPE": "00",
    "ORD_SVR_DVSN_CD": "0",
    "ORD_DVSN": "00"
}

print(f"Sending order with amount: {final_price_str}")
resp_order = requests.post(url_order, headers=t._get_headers(tr_id_order), json=body)
print(f"Sell API response: {resp_order.json()}")

time.sleep(2)
positions = t.get_positions()
for p in positions:
    print(p)

