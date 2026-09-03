import os
import sys
import requests
from dotenv import load_dotenv

# Add current dir to path
sys.path.append(os.getcwd())

from trader import get_trader
import config

def detailed_check():
    load_dotenv()
    trader = get_trader()
    
    # We'll use the trader's internal logic but print raw data
    app_key = config.KIS_APP_KEY
    app_secret = config.KIS_APP_SECRET
    account_no = config.KIS_CANO
    account_cd = config.KIS_ACNT_PRDT_CD
    
    # Ensure token is valid
    token = trader._token_mgr.get_token()
    
    tr_id = "TTTS3012R" # PROD Balance
    url = f"{trader.base_url}/uapi/overseas-stock/v1/trading/inquire-balance"
    
    for ex in ["NASD", "NYS", "AMS"]:
        print(f"\n--- Checking Exchange: {ex} ---")
        params = {
            "CANO": account_no,
            "ACNT_PRDT_CD": account_cd,
            "OVRS_EXCG_CD": ex,
            "TR_CRCY_CD": "USD",
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": ""
        }
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "authorization": f"Bearer {token}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": tr_id
        }
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            data = resp.json()
            if data.get("rt_cd") == "0":
                items = data.get("output1", [])
                if not items:
                    print(f"No positions in {ex}.")
                for item in items:
                    print(f"  Symbol: {item.get('ovrs_pdno')}, Qty: {item.get('ovrs_cblc_qty')}, Name: {item.get('prdt_name')}")
            else:
                print(f"Error for {ex}: {data.get('msg1')}")
        except Exception as e:
            print(f"Failed to check {ex}: {e}")

if __name__ == "__main__":
    detailed_check()
