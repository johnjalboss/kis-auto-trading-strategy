import os
import sys
import requests
from dotenv import load_dotenv

# Add current dir to path
sys.path.append(os.getcwd())

from trader import TokenManager
import config

def check_paper():
    load_dotenv()
    
    # Paper Trading Config
    app_key = config.KIS_APP_KEY
    app_secret = config.KIS_APP_SECRET
    account_no = config.KIS_CANO
    account_cd = config.KIS_ACNT_PRDT_CD
    base_url = "https://openapivts.koreainvestment.com:29443"
    
    # Special Token for Paper
    token_mgr = TokenManager(app_key, app_secret, base_url)
    token_mgr.TOKEN_FILE = "token_paper.json" # Use different file
    token = token_mgr.get_token()
    
    tr_id = "VTTS3012R" # Paper Balance
    url = f"{base_url}/uapi/overseas-stock/v1/trading/inquire-balance"
    
    for ex in ["NASD", "NYS", "AMS"]:
        print(f"\n--- Checking Paper Exchange: {ex} ---")
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
                    print(f"No positions in Paper {ex}.")
                for item in items:
                    print(f"  Symbol: {item.get('ovrs_pdno')}, Qty: {item.get('ovrs_cblc_qty')}, Name: {item.get('prdt_name')}")
            else:
                print(f"Error for Paper {ex}: {data.get('msg1')}")
        except Exception as e:
            print(f"Failed to check Paper {ex}: {e}")

if __name__ == "__main__":
    check_paper()
