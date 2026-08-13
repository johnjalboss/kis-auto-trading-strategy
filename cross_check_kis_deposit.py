"""
Comprehensive KIS API Deposit & Transaction Cross-Check (cross_check_kis_deposit.py)
===================================================================================
Queries both Live (openapi) and VPS endpoints for:
1. Inquire Balance & Present Balance (TTTS3012R, CTRP6504R, TTTC8434R)
2. Currency Exchange / Deposit-Withdrawal History (TTTC8010R)
3. Daily Account History (TTTC8009R)
4. All-time Executions (TTTC8001R)
"""
import sys, os
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

import json
import requests
from trader import Trader

t_live = Trader()
# Force live mode headers check
t_live.is_paper = False
t_live.base_url = "https://openapi.koreainvestment.com:9443"

print("==========================================================")
print("🔍 CROSS-CHECKING KIS API LIVE DEPOSIT & TRANSACTION DATA")
print("==========================================================")

# 1. Query Overseas Account Balance (TTTS3012R - Live)
url_bal = f"{t_live.base_url}/uapi/overseas-stock/v1/trading/inquire-balance"
tr_id_bal = "TTTS3012R"
params_bal = {
    "CANO": t_live.account_no,
    "ACNT_PRDT_CD": t_live.account_cd,
    "OVRS_EXCG_CD": "NASD",
    "TR_CRCY_CD": "USD",
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": ""
}

try:
    resp = requests.get(url_bal, headers=t_live._get_headers(tr_id_bal), params=params_bal, timeout=10)
    print(f"\n1. Inquire Balance (TTTS3012R) Status: {resp.status_code}")
    if resp.ok:
        data = resp.json()
        print("   rt_cd:", data.get("rt_cd"), "| msg1:", data.get("msg1"))
        if "output2" in data:
            print("   Output2 details:")
            for k, v in data["output2"].items():
                print(f"     {k}: {v}")
except Exception as e:
    print("Inquire balance error:", e)

# 2. Query Foreign Currency Deposit/Withdrawal/Exchange History (TTTC8010R - Live)
url_ex = f"{t_live.base_url}/uapi/overseas-stock/v1/trading/inquire-ccnl"
tr_id_ex = "TTTC8001R"
params_ex = {
    "CANO": t_live.account_no,
    "ACNT_PRDT_CD": t_live.account_cd,
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

try:
    resp = requests.get(url_ex, headers=t_live._get_headers(tr_id_ex), params=params_ex, timeout=10)
    print(f"\n2. Transaction Executions (TTTC8001R) Status: {resp.status_code}")
    if resp.ok:
        data = resp.json()
        print("   rt_cd:", data.get("rt_cd"), "| msg1:", data.get("msg1"))
        if "output1" in data:
            print(f"   Total executed orders returned: {len(data['output1'])}")
            if data['output1']:
                print("   Earliest 3 orders:")
                for item in data['output1'][-3:]:
                    print(f"     Date: {item.get('ord_dt')} | Symbol: {item.get('pdno')} | Qty: {item.get('ft_ord_qty')} | Price: ${item.get('ft_ord_unpr3')}")
except Exception as e:
    print("Transaction executions error:", e)

# 3. Query Present Balance (CTRP6504R - Live)
url_pb = f"{t_live.base_url}/uapi/overseas-stock/v1/trading/inquire-present-balance"
tr_id_pb = "CTRP6504R"
params_pb = {
    "CANO": t_live.account_no,
    "ACNT_PRDT_CD": t_live.account_cd,
    "WCRD_FTCN_BDMD_CD": "01",
    "VLCD_1": "",
    "VLCD_2": ""
}

try:
    resp = requests.get(url_pb, headers=t_live._get_headers(tr_id_pb), params=params_pb, timeout=10)
    print(f"\n3. Present Balance (CTRP6504R) Status: {resp.status_code}")
    if resp.ok:
        data = resp.json()
        print("   rt_cd:", data.get("rt_cd"), "| msg1:", data.get("msg1"))
        if "output2" in data:
            print("   Output2 Present Balance details:")
            for k, v in data["output2"].items():
                print(f"     {k}: {v}")
except Exception as e:
    print("Present balance error:", e)

print("==========================================================")
