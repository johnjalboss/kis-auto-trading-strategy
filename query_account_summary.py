"""
Query KIS API output2 from inquire-balance
"""
import sys, os
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

from trader import Trader
import json

t = Trader()
url = f"{t.base_url}/uapi/overseas-stock/v1/trading/inquire-balance"
tr_id = "VTTS3012R" if t.is_paper else "TTTS3012R"
params = {
    "CANO": t.account_no,
    "ACNT_PRDT_CD": t.account_cd,
    "OVRS_EXCG_CD": "NASD",
    "TR_CRCY_CD": "USD",
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": ""
}

import requests
try:
    resp = requests.get(url, headers=t._get_headers(tr_id), params=params, timeout=10)
    print("STATUS:", resp.status_code)
    data = resp.json()
    print("--- OUTPUT2 SUMMARY ---")
    if "output2" in data:
        print(json.dumps(data["output2"], indent=2, ensure_ascii=False))
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False)[:600])
except Exception as e:
    import traceback
    traceback.print_exc()
