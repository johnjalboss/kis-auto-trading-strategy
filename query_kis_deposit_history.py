"""
Query KIS API for Account Deposit & Foreign Exchange History (query_kis_deposit_history.py)
==========================================================================================
"""
import sys, os
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

import json
from kis_client import KISClient

client = KISClient()

print("==========================================================")
print("🔍 KIS API ACCOUNT HISTORY & DEPOSIT INQUIRY")
print("==========================================================")

# 1. Fetch Overseas Balance (tttc8434r / vtat0801r)
try:
    url = f"{client.base_url}/uapi/overseas-stock/v1/trading/inquire-present-balance"
    tr_id = "VTAT0801R" if client.is_paper else "CTRP6504R"
    headers = client._get_headers(tr_id)
    params = {
        "CANO": client.account_no,
        "ACNT_PRDT_CD": client.account_cd,
        "WCRD_FTCN_BDMD_CD": "01",
        "VLCD_1": "",
        "VLCD_2": ""
    }
    resp = client._request_with_retry("GET", url, headers=headers, params=params)
    if resp.ok:
        data = resp.json()
        print("--- OVERSEAS PRESENT BALANCE (OUTPUT2) ---")
        if "output2" in data:
            for k, v in data["output2"].items():
                print(f"  {k}: {v}")
        else:
            print("  Response:", json.dumps(data, indent=2, ensure_ascii=False)[:500])
    else:
        print("Balance API error:", resp.status_code, resp.text)
except Exception as e:
    print("Balance query exception:", e)

# 2. Fetch Account Transaction History (tttc8001r)
try:
    url = f"{client.base_url}/uapi/overseas-stock/v1/trading/inquire-ccnl"
    tr_id = "VTTC8001R" if client.is_paper else "TTTC8001R"
    headers = client._get_headers(tr_id)
    params = {
        "CANO": client.account_no,
        "ACNT_PRDT_CD": client.account_cd,
        "PDNO": "%",
        "ORD_STRT_DT": "20260101",
        "ORD_END_DT": "20260814",
        "SLL_BUY_DVSN_CD": "00",
        "CCNL_DVSN": "00",
        "ORD_GNO_BRNO": "",
        "ODNO": "",
        "INQR_DVSN_01": "00",
        "INQR_DVSN_02": "00",
        "CTX_AREA_NK200": "",
        "CTX_AREA_FK200": ""
    }
    resp = client._request_with_retry("GET", url, headers=headers, params=params)
    if resp.ok:
        data = resp.json()
        print("\n--- ACCOUNT TRANSACTION HISTORY ---")
        if "output1" in data and data["output1"]:
            print(f"Total transactions found: {len(data['output1'])}")
            for tx in data["output1"][-5:]:  # Earliest transactions
                print(f"  Date: {tx.get('ord_dt')} | Symbol: {tx.get('pdno')} | Side: {tx.get('sll_buy_dvsn_cd_name')} | Qty: {tx.get('ft_ord_qty')} | Price: ${tx.get('ft_ord_unpr3')}")
        else:
            print("  No transaction history returned from API.")
    else:
        print("Transaction history API status:", resp.status_code)
except Exception as e:
    print("Transaction query exception:", e)

print("==========================================================")
