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

def get_exact_mapping():
    token = get_token()
    base_url = "https://openapi.koreainvestment.com:9443"
    api_url = f"{base_url}/uapi/overseas-stock/v1/trading/inquire-balance"
    
    cano = os.getenv("KIS_CANO")
    prdt_code = os.getenv("KIS_ACNT_PRDT_CD", "01")
    
    # KIS requires checking per exchange, but let's check ALL known ones
    exchanges = ["NASD", "NYSE", "AMEX"]
    
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
                if item.get("pdno") == "PLTD":
                    print(f"SYMBOL: PLTD | KIS_REPORTED_EXCHANGE: {exch}")
                    return True
    return False

if __name__ == "__main__":
    if not get_exact_mapping():
        print("PLTD not found in balance across NASD, NYSE, AMEX.")
