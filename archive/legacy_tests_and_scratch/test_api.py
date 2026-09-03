import requests, json, sys, os
from dotenv import load_dotenv

load_dotenv()
try:
    token = json.load(open('token.json'))['access_token']
except:
    print("No token")
    sys.exit(1)

app_key = os.getenv('KIS_APP_KEY')
app_secret = os.getenv('KIS_APP_SECRET')
account_no = os.getenv('KIS_CANO')
account_cd = os.getenv('KIS_ACNT_PRDT_CD')
is_paper = str(os.getenv('IS_PAPER_TRADING')).lower() in ['true', '1']

base_url = "https://openapivts.koreainvestment.com:29443" if is_paper else "https://openapi.koreainvestment.com:9443"
url = f"{base_url}/uapi/overseas-stock/v1/trading/inquire-balance"
tr_id = "VTTS3012R" if is_paper else "TTTS3012R"

headers = {
    'Content-Type': 'application/json',
    'authorization': f'Bearer {token}',
    'appkey': app_key,
    'appsecret': app_secret,
    'tr_id': tr_id
}

for excd in ['NASD', 'NYSE', 'AMEX']:
    params = {
        'CANO': account_no,
        'ACNT_PRDT_CD': account_cd,
        'OVRS_EXCG_CD': excd,
        'TR_CRCY_CD': 'USD',
        'CTX_AREA_FK200': '',
        'CTX_AREA_NK200': ''
    }
    r = requests.get(url, headers=headers, params=params)
    print(f"\\n=== EXCD: {excd} ===")
    out = r.json().get('output1', [])
    for item in out:
        qty = int(item.get('ovrs_cblc_qty', 0))
        if qty > 0:
            print(f"  {item.get('ovrs_pdno')}: {qty}")
