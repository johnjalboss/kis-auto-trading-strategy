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

def diagnose_pltd():
    token = get_token()
    base_url = "https://openapi.koreainvestment.com:9443"
    
    # 1. Check Balance across exchanges
    balance_url = f"{base_url}/uapi/overseas-stock/v1/trading/inquire-balance"
    exchanges = ["NASD", "NYSE", "AMEX", "NAS", "NYS", "AMS"]
    
    print("=== Position Check ===")
    for exch in exchanges:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "appkey": os.getenv("KIS_APP_KEY"),
            "appsecret": os.getenv("KIS_APP_SECRET"),
            "tr_id": "JTTT3012R",
            "custtype": "P"
        }
        params = {
            "CANO": os.getenv("KIS_CANO"),
            "ACNT_PRDT_CD": os.getenv("KIS_ACNT_PRDT_CD", "01"),
            "OVRS_EXCH_CD": exch,
            "TR_CRC_CD": "USD",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }
        resp = requests.get(balance_url, headers=headers, params=params)
        data = resp.json()
        if data.get("rt_cd") == "0":
            for item in data.get("output1", []):
                if item.get("pdno") == "PLTD":
                    print(f"  MATCH FOUND under {exch}: {item.get('ovrs_cblc_qty')} shares")
    
    # 2. Check Price across exchanges
    price_url = f"{base_url}/uapi/overseas-price/v1/quotations/price"
    print("\n=== Price Check ===")
    for exch in exchanges:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "appkey": os.getenv("KIS_APP_KEY"),
            "appsecret": os.getenv("KIS_APP_SECRET"),
            "tr_id": "HHDFS00000300",
            "custtype": "P"
        }
        params = {"AUTH": "", "EXCD": exch, "SYMB": "PLTD"}
        resp = requests.get(price_url, headers=headers, params=params)
        data = resp.json()
        if data.get("rt_cd") == "0":
            print(f"  Price Success under {exch}: ${data.get('output', {}).get('last')}")

if __name__ == "__main__":
    diagnose_pltd()
