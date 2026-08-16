"""
Query 100% Real Live KIS Broker Account Balance & Order History via KIS API
Extracts actual cash balance, total portfolio evaluation value, open positions,
and executed order count directly from Korea Investment & Securities (KIS) API!
"""
import sys, os, requests, json
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

from trader import Trader

print("==========================================================")
print("🔍 DIRECT KIS BROKER API REAL ACCOUNT INQUIRY")
print("==========================================================")

t = Trader()
tr_id = "VTTS3012R" if t.is_paper else "TTTS3012R"
url = f"{t.base_url}/uapi/overseas-stock/v1/trading/inquire-balance"

params = {
    "CANO": t.account_no,
    "ACNT_PRDT_CD": t.account_cd,
    "OVRS_EXCG_CD": "NASD",
    "TR_CRCY_CD": "USD",
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": ""
}

try:
    resp = requests.get(url, headers=t._get_headers(tr_id), params=params, timeout=15)
    data = resp.json()
    print("KIS API Response Code:", data.get("rt_cd"), "Msg:", data.get("msg1"))
    
    output1 = data.get("output1", [])
    output2 = data.get("output2", {})
    
    print("\n1. KIS API Account Portfolio Evaluation (output2):")
    if isinstance(output2, dict):
        for k, v in output2.items():
            if v:
                print(f"   {k}: {v}")
    elif isinstance(output2, list) and output2:
        for k, v in output2[0].items():
            if v:
                print(f"   {k}: {v}")
                
    print(f"\n2. KIS API Open Positions (output1 count: {len(output1)}):")
    for item in output1:
        qty = item.get("ovrs_cblc_qty", "0")
        sym = item.get("ovrs_pdno", "")
        avg_p = item.get("pchs_avg_pric", "0")
        now_p = item.get("now_pric2", "0")
        pnl = item.get("frcr_evlu_pfls_amt", "0")
        print(f"   - {sym}: Qty {qty}, Avg ${avg_p}, Now ${now_p}, PnL ${pnl}")
        
    bp = t.get_buying_power()
    print(f"\n3. KIS API Real Buying Power: ${bp:,.2f}")
    
except Exception as e:
    print("KIS API Query Error:", e)

# Query Executed Orders History via KIS API (inquire-ccnl TTTS3035R / VTTS3035R)
print("\n4. KIS API Executed Orders Inquiry (inquire-ccnl):")
ccnl_tr_id = "VTTS3035R" if t.is_paper else "TTTS3035R"
ccnl_url = f"{t.base_url}/uapi/overseas-stock/v1/trading/inquire-ccnl"

ccnl_params = {
    "CANO": t.account_no,
    "ACNT_PRDT_CD": t.account_cd,
    "PDNO": "%",
    "ORD_STRT_DT": "20260201",
    "ORD_END_DT": "20260814",
    "SLL_BUY_DVSN": "00",
    "CCLD_NCCL_DVSN": "01", # 01: 체결만 (Executed orders)
    "OVRS_EXCG_CD": "%",
    "SORT_SQN": "DS",
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": ""
}

try:
    c_resp = requests.get(ccnl_url, headers=t._get_headers(ccnl_tr_id), params=ccnl_params, timeout=15)
    c_data = c_resp.json()
    print("   Executed Orders Query Code:", c_data.get("rt_cd"), "Msg:", c_data.get("msg1"))
    c_output = c_data.get("output", [])
    print(f"   Total Executed Orders Returned by KIS API: {len(c_output)} orders")
    if c_output:
        print("   Sample executed orders (first 5):")
        for ord_item in c_output[:5]:
            print(f"     - Date: {ord_item.get('ord_dt')}, Symbol: {ord_item.get('pdno')}, Side: {ord_item.get('sll_buy_dvsn_cd')}, Qty: {ord_item.get('ft_ord_qty')}, Price: ${ord_item.get('ft_ord_unpr')}")
except Exception as ce:
    print("   Executed Orders Query Error:", ce)

print("==========================================================")
