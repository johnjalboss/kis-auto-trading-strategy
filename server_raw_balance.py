import json
import os
import sys
import requests
from loguru import logger

sys.path.append(os.getcwd())

import config
from trader import get_trader

def dump_raw_balance():
    trader = get_trader()
    tr_id = "VTTS3012R" if trader.is_paper else "TTTS3012R"
    url = f"{trader.base_url}/uapi/overseas-stock/v1/trading/inquire-balance"
    
    params = {
        "CANO": trader.account_no,
        "ACNT_PRDT_CD": trader.account_cd,
        "OVRS_EXCG_CD": "NASD",
        "TR_CRCY_CD": "USD",
        "CTX_AREA_FK200": "",
        "CTX_AREA_NK200": ""
    }
    
    try:
        resp = requests.get(url, headers=trader._get_headers(tr_id),
                          params=params, timeout=10)
        data = resp.json()
        print("\nRAW BALANCE DATA:")
        print(json.dumps(data, indent=2))
        
        # Also try other exchanges just in case
        for excg in ["NYS", "AMS"]:
            params["OVRS_EXCG_CD"] = excg
            resp = requests.get(url, headers=trader._get_headers(tr_id),
                              params=params, timeout=10)
            print(f"\nRAW BALANCE DATA ({excg}):")
            print(json.dumps(resp.json(), indent=2))
            
    except Exception as e:
        print(f"FAILED TO DUMP: {e}")

if __name__ == "__main__":
    dump_raw_balance()
