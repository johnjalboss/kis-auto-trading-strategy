import sys, os
os.chdir('c:/Users/wngud/.gemini/antigravity/scratch/kis-auto-trading')
sys.path.insert(0, 'c:/Users/wngud/.gemini/antigravity/scratch/kis-auto-trading')

import config
from auth import get_auth
import requests
import json

def test_api():
    auth = get_auth()
    
    print("Testing New High API with discovered params...")
    headers = auth.get_headers(tr_id="HHDFS76300000")
    params = {
        "AUTH": "",
        "EXCD": "NAS",  
        "GUBN": "1",    # 1: 신고가
        "GUBN2": "0",   # 0: 당일?
        "NDAY": "6",    # 6: 52주
        "VOL_RANG": "0", # 0: 전체
        "KEYB": ""
    }
    
    resp = requests.get(
        f"{config.BASE_URL}/uapi/overseas-stock/v1/ranking/new-highlow",
        headers=headers,
        params=params
    )
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:300]}")

    print("\nTesting Top Value API with discovered params...")
    headers = auth.get_headers(tr_id="HHDFS76200200") # Still unsure about TR_ID, might fail
    params = {
        "AUTH": "",
        "EXCD": "NAS",
        "NDAY": "0",
        "VOL_RANG": "0",
        "PRC1": "0",
        "PRC2": "9999",
        "KEYB": ""
    }
    resp = requests.get(
        f"{config.BASE_URL}/uapi/overseas-stock/v1/ranking/trading-volume",
        headers=headers,
        params=params
    )
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:300]}")


if __name__ == "__main__":
    test_api()
