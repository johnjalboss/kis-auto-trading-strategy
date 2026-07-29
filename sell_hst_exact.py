import sys
sys.path.append('/home/ubuntu/kis-auto-trading')

import trader
import requests
import time
t = trader.get_trader()
t.start()

# Get Orderbook (Hoka) to find the exact best bid price
symbol = 'HST'
exchange = 'NASD'
tr_id = "HHDFS00000300" # Price API uses same auth style
url = f"{t.base_url}/uapi/overseas-price/v1/quotations/price"

params = {"AUTH": "", "EXCD": exchange, "SYMB": symbol}

try:
    resp = requests.get(url, headers=t._get_headers(tr_id), params=params)
    data = resp.json()
    if data.get("rt_cd") == "0":
        output = data.get("output", {})
        # tp_pbid1: 매수호가1 (Best Bid)
        # last: 현재가 (Last)
        best_bid = output.get("tvar", "") # tvla? tp_pbid1? let's try pbid1 first if available, otherwise 'last'
        # Actually standard price API returns 'last', 'sign', 'diff', 'rate', 'tvol', 'tamt', 'h52p', 'l52p' 
        # For actual orderbook we'd need another endpoint, let's just trace the returned object
        
        # Another approach: try setting order division to Market Order or LOC
        pass
except Exception as e:
    print(e)

# Let's try fetching the orderbook or using a very specific price format exactly matched to 'last'
price_str = data.get("output", {}).get("last", "0.00")
print(f"Exact last price string from API: {price_str}")

# Create Limit order at exactly the 'last' price string
url_order = f'{t.base_url}/uapi/overseas-stock/v1/trading/order'
tr_id_order = 'VTTT1001U' if t.is_paper else 'TTTT1006U'

body = {
    "CANO": t.account_no,
    "ACNT_PRDT_CD": t.account_cd,
    "OVRS_EXCG_CD": exchange,
    "PDNO": symbol,
    "ORD_QTY": "1",
    "OVRS_ORD_UNPR": price_str,  # Use exact string from KIS
    "SLL_TYPE": "00",
    "ORD_SVR_DVSN_CD": "0",
    "ORD_DVSN": "00"
}

print(f"Sending order with amount: {price_str}")
resp_order = requests.post(url_order, headers=t._get_headers(tr_id_order), json=body)
print(f"Sell API response: {resp_order.json()}")

time.sleep(2)
positions = t.get_positions()
for p in positions:
    print(p)
