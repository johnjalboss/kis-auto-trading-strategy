"""
Query executed orders from KIS API across specific exchange codes (NASD, NYSE, AMEX)
"""
import sys, os, requests, json

sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

from trader import Trader

t = Trader()
ccnl_tr_id = "VTTS3035R" if t.is_paper else "TTTS3035R"
ccnl_url = f"{t.base_url}/uapi/overseas-stock/v1/trading/inquire-ccnl"

print("==========================================================")
print("🔍 FETCHING EXECUTED ORDERS BY EXCHANGE FROM KIS API")
print("==========================================================")

all_orders = []
exchanges = ["NASD", "NYSE", "AMEX"]

for excd in exchanges:
    params = {
        "CANO": t.account_no,
        "ACNT_PRDT_CD": t.account_cd,
        "PDNO": "",
        "ORD_STRT_DT": "20260515",
        "ORD_END_DT": "20260814",
        "SLL_BUY_DVSN": "00",
        "CCLD_NCCL_DVSN": "01",
        "OVRS_EXCG_CD": excd,
        "SORT_SQN": "DS",
        "CTX_AREA_FK200": "",
        "CTX_AREA_NK200": ""
    }
    try:
        resp = requests.get(ccnl_url, headers=t._get_headers(ccnl_tr_id), params=params, timeout=10)
        data = resp.json()
        orders = data.get("output", [])
        print(f"Exchange {excd}: Code={data.get('rt_cd')}, Orders Count={len(orders)}")
        if orders:
            for o in orders:
                print("  ", o)
                all_orders.append(o)
    except Exception as e:
        print(f"Exchange {excd} error: {e}")

print(f"\nTotal Executed Orders Fetched: {len(all_orders)}")
print("==========================================================")
