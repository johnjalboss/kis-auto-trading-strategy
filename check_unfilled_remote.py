import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def get_token():
    url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
    payload = {
        "grant_type": "client_credentials",
        "appkey": os.getenv("KIS_APP_KEY"),
        "appsecret": os.getenv("KIS_APP_SECRET")
    }
    resp = requests.post(url, json=payload)
    return resp.json().get("access_token")

def check_unfilled():
    token = get_token()
    base_url = "https://openapi.koreainvestment.com:9443"
    api_url = f"{base_url}/uapi/overseas-stock/v1/trading/inquire-nccs-order"
    
    cano = os.getenv("KIS_CANO")
    prdt_code = os.getenv("KIS_ACNT_PRDT_CD", "01")
    
    # KIS requires checking per exchange
    exchanges = ["NASD", "NYSE", "AMEX"]
    
    print(f"Checking Open Orders for: {cano}")
    found = False
    for exch in exchanges:
        print(f"Checking Exchange: {exch}")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "appkey": os.getenv("KIS_APP_KEY"),
            "appsecret": os.getenv("KIS_APP_SECRET"),
            "tr_id": "JTTT3001R", # Overseas Unfilled query
            "custtype": "P"
        }
        params = {
            "CANO": cano,
            "ACNT_PRDT_CD": prdt_code,
            "OVRS_EXCH_CD": exch,
            "SORT_SQN": "DS",
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": ""
        }
        resp = requests.get(api_url, headers=headers, params=params)
        data = resp.json()
        if data.get("rt_cd") == "0":
            for item in data.get("output", []):
                print(f"  OPEN ORDER: {item.get('pdno')} | Type: {item.get('sll_buy_dvsn_cd')} | Qty: {item.get('unfc_qty')} | Org: {item.get('orgn_odno')}")
                found = True
        else:
            print(f"  Error {exch}: {data.get('msg1')}")
            
    if not found:
        print("No open orders found.")

if __name__ == "__main__":
    check_unfilled()
