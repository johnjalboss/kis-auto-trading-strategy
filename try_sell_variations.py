import os
import requests
import json
from trader import get_trader

def get_token():
    t = get_trader()
    return t.get_token()

def try_sell_variations():
    token = get_token()
    base_url = "https://openapi.koreainvestment.com:9443"
    api_url = f"{base_url}/uapi/overseas-stock/v1/trading/order"
    
    symbol = "PLTD"
    price = 7.25 # From previous check
    cano = os.getenv("KIS_CANO")
    acnt = os.getenv("KIS_ACNT_PRDT_CD", "01")
    
    # Try different exchange codes for the order
    # We know price works under NAS
    # We know balance shows under NYS
    order_exchanges = ["NASD", "NYSE", "AMEX", "NAS", "NYS", "AMS"]
    
    print(f"Attempting variant sell orders for {symbol} @ {price}")
    
    for ex in order_exchanges:
        print(f"\n--- Trying Order Exchange: {ex} ---")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "appkey": os.getenv("KIS_APP_KEY"),
            "appsecret": os.getenv("KIS_APP_SECRET"),
            "tr_id": "TTTT1006U", # REAL Overseas SELL
            "custtype": "P"
        }
        
        body = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt,
            "OVRS_EXCG_CD": ex,
            "PDNO": symbol,
            "ORD_QTY": "1",
            "OVRS_ORD_UNPR": f"{price:.2f}",
            "SLL_TYPE": "00",
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": "00"
        }
        
        resp = requests.post(api_url, headers=headers, json=body)
        data = resp.json()
        print(f"  Result: {data.get('rt_cd')} | {data.get('msg1')}")
        if data.get("rt_cd") == "0":
            print(f"  SUCCESS! Order No: {data.get('output', {}).get('ODNO')}")
            return # Stop if one succeeds

if __name__ == "__main__":
    try_sell_variations()
