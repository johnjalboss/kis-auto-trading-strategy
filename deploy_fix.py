import subprocess
import os

def run_ssh(cmd_str):
    ssh_cmd = ['C:\\Windows\\System32\\OpenSSH\\ssh.exe', '-i', 'id_rsa', '-o', 'StrictHostKeyChecking=no', 'ubuntu@141.148.172.12', cmd_str]
    return subprocess.run(ssh_cmd, capture_output=True, text=True)

# 1. Update remote_orchestrator.py
update_script = """
import os
path = '/home/ubuntu/kis-auto-trading/remote_orchestrator.py'
with open(path, 'r') as f:
    content = f.read()

old = '''        # 4. Kelly Criterion + Position Sizing
        try:
            from position_sizer import calculate_optimal_size
            from kelly_criterion import get_kelly_fraction
            kelly_pct = get_kelly_fraction(symbol)
            qty = calculate_optimal_size(symbol, qty, kelly_pct, self.state.max_exposure_pct)
        except Exception as err:
            logger.warning("⚠️ [deploy_fix.py] Fallback triggered: {}", err)
            
        if qty <= 0:
            logger.warning("Risk modules reduced size to 0 for {}", symbol)
            return'''

new = '''        # 4. Kelly Criterion + Position Sizing (ONLY for BUY orders)
        if action == "BUY":
            try:
                from position_sizer import calculate_optimal_size
                from kelly_criterion import get_kelly_fraction
                kelly_pct = get_kelly_fraction(symbol)
                qty = calculate_optimal_size(symbol, qty, kelly_pct, self.state.max_exposure_pct)
            except Exception as err:
                logger.warning("⚠️ [deploy_fix.py] Fallback triggered: {}", err)
            
            if qty <= 0:
                logger.warning("Risk modules reduced size to 0 for {}", symbol)
                return
        else:
            # For SELL/CLOSE, ensure we use the full requested quantity
            pass'''

if old in content:
    with open(path, 'w') as f:
        f.write(content.replace(old, new))
    print("SUCCESS")
else:
    print("NOT FOUND")
"""

with open('remote_fix.py', 'w') as f:
    f.write(update_script)

res = run_ssh(f"cat > /tmp/remote_fix.py <<'EOF'\n{update_script}\nEOF\npython3 /tmp/remote_fix.py && sudo systemctl restart kis-trading")
print(res.stdout)
print(res.stderr)

# 2. Detailed KIS Balance Check
balance_script = """
import sys, os, requests
sys.path.append('/home/ubuntu/kis-auto-trading')
import trader
t = trader.get_trader()
t.start()
for ex in ['NASD', 'NYS', 'AMS']:
    url = f'{t.base_url}/uapi/overseas-stock/v1/trading/inquire-balance'
    tr_id = 'VTTS3012R' if t.is_paper else 'TTTS3012R'
    params = {'CANO': t.account_no, 'ACNT_PRDT_CD': t.account_cd, 'OVRS_EXCG_CD': ex, 'TR_CRCY_CD': 'USD', 'CTX_AREA_FK200': '', 'CTX_AREA_NK200': ''}
    resp = requests.get(url, headers=t._get_headers(tr_id), params=params)
    data = resp.json()
    if data.get('rt_cd') == '0':
        for item in data.get('output1', []):
            if item.get('ovrs_pdno') == 'HST':
                print(f"EX: {ex}, QTY: {item.get('ovrs_cblc_qty')}, SELLABLE: {item.get('ord_psbl_qty')}")
"""

res = run_ssh(f"cat > /tmp/check_bal.py <<'EOF'\n{balance_script}\nEOF\npython3 /tmp/check_bal.py")
print(res.stdout)
print(res.stderr)
