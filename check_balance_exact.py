import os
import requests
import json
from auth import TokenManager

def check_balance_exact():
    tm = TokenManager()
    token = tm.get_token()
    
    base_url = "https://openapi.koreainvestment.com:9443"
    api_url = f"{base_url}/uapi/overseas-stock/v1/trading/inquire-balance"
    
    cano = os.getenv("KIS_CANO")
    prdt_code = os.getenv("KIS_ACNT_PRDT_CD", "01")
    
    # Try all possible exchange codes
    exchanges = ["NASD", "NYSE", "AMEX", "NAS", "NYS", "AMS"]
    
    print(f"Checking account: {cano}-{prdt_code}")
    
    for exch in exchanges:
        print(f"\n--- Exchange: {exch} ---")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "appkey": os.getenv("KIS_APP_KEY"),
            "appsecret": os.getenv("KIS_APP_SECRET"),
            "tr_id": "JTTT3012R", # Overseas balance TR ID
            "custtype": "P"
        }
        
        params = {
            "CANO": cano,
            "ACNT_PRDT_CD": prdt_code,
            "OVRS_EXCH_CD": exch,
            "TR_CRC_CD": "USD",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }
        
        resp = requests.get(api_url, headers=headers, params=params)
        data = resp.json()
        
        if data.get("rt_cd") == "0":
            for item in data.get("output1", []):
                print(f"  {item.get('pdno')} | {item.get('ovrs_item_name')} | Qty: {item.get('ovrs_cblc_qty')}")
        else:
            print(f"  Error: {data.get('msg1')}")

if __name__ == "__main__":
    check_balance_exact()
