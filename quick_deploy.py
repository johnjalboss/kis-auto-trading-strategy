import subprocess
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

KEY = 'id_rsa'
SERVER = 'ubuntu@141.148.172.12'
REMOTE_DIR = '/home/ubuntu/kis-auto-trading'

CHANGED_FILES = [
    'config.py',
    'position_sizer.py',
    'strategy.py',
    'screener.py',
    'orchestrator.py',
    'orchestrator_remote.py',
    'news_analyzer.py',
    'smart_order.py',
    'options_flow.py',
    'kis_data.py',
    'earnings_analyzer.py',
    'macro_news_analyzer.py',
]

def run_scp(local_file):
    cmd = ['scp', '-i', KEY, '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=10', local_file, f'{SERVER}:{REMOTE_DIR}/{local_file}']
    print(f"Uploading {local_file}...")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode == 0:
        print(f"  [OK] {local_file}")
        return True
    else:
        print(f"  [FAIL] {local_file}")
        print(f"  Error: {res.stderr.decode('utf-8', errors='ignore')}")
        return False

def run_ssh(remote_cmd):
    cmd = ['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=10', SERVER, remote_cmd]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return res.returncode, res.stdout.decode('utf-8', errors='ignore'), res.stderr.decode('utf-8', errors='ignore')

def main():
    print("=" * 60)
    print("STARTING WINDOWS COMPATIBLE QUICK DEPLOY (PROD)")
    print("=" * 60)
    
    # 1. SCP
    success_count = 0
    for f in CHANGED_FILES:
        if run_scp(f):
            success_count += 1
            
    print(f"\nUpload summary: {success_count}/{len(CHANGED_FILES)} successful.")
    
    # 2. Clear __pycache__
    print("\nClearing remote __pycache__...")
    rc, out, err = run_ssh("find /home/ubuntu/kis-auto-trading -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null; echo DONE")
    print(f"  Result: {out.strip()} (rc={rc})")
    
    # 3. Restart service
    print("\nRestarting kis-trading systemd service...")
    rc, out, err = run_ssh("sudo systemctl restart kis-trading")
    print(f"  Restart code: {rc}")
    if err.strip():
        print(f"  Error: {err.strip()}")
        
    # 4. Check active status
    print("\nVerifying service status...")
    rc, out, err = run_ssh("systemctl is-active kis-trading")
    status = out.strip()
    print(f"  Active status: {status}")
    
    # 5. Check last log lines
    print("\nFetching last 10 lines of remote log...")
    rc, out, err = run_ssh("tail -n 10 /home/ubuntu/kis-auto-trading/remote_trading_bot.log")
    print("----- REMOTE LOG START -----")
    print(out)
    print("----- REMOTE LOG END -----")
    
    print("=" * 60)
    if status == 'active':
        print("DEPLOYMENT & RESTART SUCCESSFUL!")
    else:
        print("WARNING: Service might not be running. Check systemd logs.")
    print("=" * 60)

if __name__ == '__main__':
    main()
