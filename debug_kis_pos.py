import sys
import os
import requests
from loguru import logger

# Add current dir to path
sys.path.append(os.getcwd())

from trader import get_trader
import config

def debug_kis_positions():
    trader = get_trader()
    trader.start()
    
    tr_id = "VTTS3012R" if trader.is_paper else "TTTS3012R"
    url = f"{trader.base_url}/uapi/overseas-stock/v1/trading/inquire-balance"
    
    for exchange_code in ["NASD", "NYS", "AMS", "NAS", "NYS", "AMS"]: # Try both 4-char and 3-char
        params = {
            "CANO": trader.account_no,
            "ACNT_PRDT_CD": trader.account_cd,
            "OVRS_EXCG_CD": exchange_code,
            "TR_CRCY_CD": "USD",
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": ""
        }
        
        print(f"\n--- Checking Exchange: {exchange_code} ---")
        try:
            resp = requests.get(url, headers=trader._get_headers(tr_id),
                              params=params, timeout=10)
            data = resp.json()
            print(f"Response Code: {data.get('rt_cd')}")
            print(f"Message: {data.get('msg1')}")
            
            if data.get("rt_cd") == "0":
                output1 = data.get("output1", [])
                if not output1:
                    print("No positions in this exchange.")
                for item in output1:
                    print(f"  Pos: {item.get('ovrs_pdno')} | Qty: {item.get('ovrs_cblc_qty')} | Avg: {item.get('pchs_avg_pric')}")
        except Exception as e:
            print(f"Error: {e}")
            
    trader.stop()

if __name__ == "__main__":
    debug_kis_positions()
