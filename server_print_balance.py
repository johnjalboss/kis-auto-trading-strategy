import os
import sys
import requests
import json

sys.path.append(os.getcwd())
import config
from trader import get_trader

def print_clean_balance():
    trader = get_trader()
    tr_id = "VTTS3012R" if trader.is_paper else "TTTS3012R"
    url = f"{trader.base_url}/uapi/overseas-stock/v1/trading/inquire-balance"
    
    # Try all exchanges to be sure
    exchanges = ["NASD", "NYS", "AMEX"]
    found = False
    
    for excg in exchanges:
        params = {
            "CANO": trader.account_no,
            "ACNT_PRDT_CD": trader.account_cd,
            "OVRS_EXCG_CD": excg,
            "TR_CRCY_CD": "USD",
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": ""
        }
        
        try:
            resp = requests.get(url, headers=trader._get_headers(tr_id), params=params, timeout=10)
            data = resp.json()
            output1 = data.get("output1", [])
            if output1:
                print(f"\n--- {excg} POSITIONS ---")
                for item in output1:
                    qty_str = item.get("ovrs_cblc_qty", "0")
                    if qty_str and int(float(qty_str)) > 0:
                        symbol = item.get("ovrs_pdno", "")
                        avg = item.get("pchs_avg_pric", "0")
                        curr = item.get("now_pric2", "0")
                        print(f"SYMBOL: {symbol:10} QTY: {qty_str:5} AVG: {avg:10} CURR: {curr:10}")
                        found = True
        except Exception as e:
            print(f"Error checking {excg}: {e}")
            
    if not found:
        print("\nNo active positions found in any exchange.")

if __name__ == "__main__":
    print_clean_balance()
