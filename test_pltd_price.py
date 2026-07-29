import os
import requests
import json
from auth import TokenManager

def test_price_exchanges():
    tm = TokenManager()
    token = tm.get_token()
    
    base_url = "https://openapi.koreainvestment.com:9443"
    api_url = f"{base_url}/uapi/overseas-price/v1/quotations/price"
    
    symbol = "PLTD"
    exchanges = ["NASD", "NYSE", "AMEX", "NAS", "NYS", "AMS"]
    
    print(f"Testing Price Query for {symbol}")
    
    for exch in exchanges:
        print(f"\n--- Exchange: {exch} ---")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "appkey": os.getenv("KIS_APP_KEY"),
            "appsecret": os.getenv("KIS_APP_SECRET"),
            "tr_id": "HHDFS00000300", # Overseas price TR ID
            "custtype": "P"
        }
        
        params = {
            "AUTH": "",
            "EXCD": exch,
            "SYMB": symbol
        }
        
        resp = requests.get(api_url, headers=headers, params=params)
        data = resp.json()
        
        if data.get("rt_cd") == "0":
            output = data.get("output", {})
            print(f"  Success! Price: {output.get('last')}")
        else:
            print(f"  Error: {data.get('msg1')}")

if __name__ == "__main__":
    test_price_exchanges()
