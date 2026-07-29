import sys, os
os.chdir('/home/ubuntu/kis-auto-trading')
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')

import config
from auth import get_auth
import requests
import json

def test_api():
    auth = get_auth()
    
    # 1. 해외주식 신고가 (New High)
    print("Testing New High API...")
    headers = auth.get_headers(tr_id="HHDFS76300000")
    params = {
        "AUTH": "",
        "EXCD": "NAS",  # NASDAQ
        "PRDT_TYPE_CD": "512", # 주식
        "RANK_SORT_CLS_CODE": "1", # 신고가
        "KEYB": ""
    }
    resp = requests.get(
        f"{config.BASE_URL}/uapi/overseas-stock/v1/ranking/new-highlow",
        headers=headers,
        params=params
    )
    print(f"Status: {resp.status_code}")
    try:
        data = resp.json()
        print(f"Message: {data.get('msg1')}")
        if data.get('output1'):
            print(f"Found {len(data['output1'])} records")
            for r in data['output1'][:3]:
                print(f"  {r.get('symb')}: {r.get('prpr')} (New High)")
    except Exception as e:
        print(e)
        print(resp.text[:500])

    print("\n--------------------------")
    # 2. 해외주식 거래대금 순위 (Top Value)
    print("Testing Top Value API...")
    headers = auth.get_headers(tr_id="HHDFS76200200") # Might be wrong TR_ID, just testing if it gives helpful error
    params = {
        "AUTH": "",
        "EXCD": "NAS",
        "PRDT_TYPE_CD": "512",
        "KEYB": ""
    }
    resp = requests.get(
        f"{config.BASE_URL}/uapi/overseas-stock/v1/ranking/trading-volume",
        headers=headers,
        params=params
    )
    print(f"Status: {resp.status_code}")
    try:
        data = resp.json()
        print(f"Message: {data.get('msg1')}")
        if data.get('output1'):
            print(f"Found {len(data['output1'])} records")
    except Exception as e:
        print(e)
        print(resp.text[:500])

if __name__ == "__main__":
    test_api()
