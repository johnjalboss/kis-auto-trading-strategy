"""
Final PLTD sell script - uses Trader internals for auth, tries all exchange codes.
"""
import os, requests
from trader import get_trader

def main():
    t = get_trader()
    token = t._token_mgr.get_token()
    cano = t.account_no
    acnt = t.account_cd
    app_key = t.app_key
    app_secret = t.app_secret
    base_url = t.base_url

    symbol = "PLTD"
    # NAS is confirmed to return a valid price
    price = t.get_price(symbol, "NAS")
    if price <= 0:
        price = 7.22
        print(f"Price fetch failed, using fallback: {price}")
    else:
        print(f"Current PLTD price (via NAS): {price}")

    url = f"{base_url}/uapi/overseas-stock/v1/trading/order"
    tr_id = "VTTT1001U" if t.is_paper else "TTTT1006U"
    print(f"is_paper={t.is_paper}, tr_id={tr_id}, base_url={base_url}")

    for ex in ["NASD", "NYSE", "AMEX", "NAS", "NYS", "AMS"]:
        print(f"\n=== Trying exchange: {ex} ===")
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "authorization": f"Bearer {token}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": tr_id,
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
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=10)
            data = resp.json()
            rt_cd = data.get("rt_cd", "?")
            msg = data.get("msg1", "").strip()
            odno = data.get("output", {}).get("ODNO", "")
            print(f"  rt_cd={rt_cd} | msg={msg} | order_no={odno}")
            if rt_cd == "0":
                print(f"\n SUCCESS! Order placed with exchange={ex}, order_no={odno}")
                return
        except Exception as e:
            print(f"  Error: {e}")

    print("\n All exchange codes failed. Check messages above.")

if __name__ == "__main__":
    main()
