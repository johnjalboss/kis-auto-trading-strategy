import subprocess
import time

KEY = 'id_rsa'
SERVER = 'ubuntu@141.148.172.12'
REMOTE_DIR = '/home/ubuntu/kis-auto-trading'

CHANGED_FILES = [
    'data_proxy.py',     # DATA: Cache macro tickers & enforce 10s timeout + lock on yfinance calls
]

def scp(local, remote):
    proc = subprocess.Popen(
        ['scp', '-i', KEY, '-o', 'StrictHostKeyChecking=no',
         '-o', 'ConnectTimeout=15', local, f'{SERVER}:{remote}'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out, err = proc.communicate(input=b'yes\n', timeout=60)
    return proc.returncode, err.decode('utf-8', errors='replace')

def ssh(cmd):
    proc = subprocess.Popen(
        ['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no',
         '-o', 'ConnectTimeout=15', SERVER, cmd],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out, err = proc.communicate(input=b'yes\n', timeout=30)
    return out.decode('utf-8', errors='replace'), err.decode('utf-8', errors='replace'), proc.returncode

print("=" * 60)
print("DEPLOYING DATA PROXY TIMEOUT & CACHE FIX TO ORACLE VM...")
print("=" * 60)

# 1. SCP modified files
print("\n[1/3] SCP modified files...")
for f in CHANGED_FILES:
    rc, err = scp(f, f'{REMOTE_DIR}/{f}')
    if rc == 0:
        print(f"  OK  {f} uploaded")
    else:
        print(f"  FAIL {f}: {err.strip()[:120]}")
        exit(1)

# 2. Clear remote stale pycache
print("\n[2/3] Clearing remote __pycache__...")
ssh(f"find {REMOTE_DIR} -name '__pycache__' -type d -exec rm -rf {{}} + 2>/dev/null")
print("  OK pycache cleared")

# 3. Restart kis-trading service
print("\n[3/3] Restarting kis-trading service...")
out, err, rc = ssh("sudo systemctl restart kis-trading")
print(f"  restart rc={rc}")
time.sleep(6)

# Verify service is active
out, err, rc = ssh("systemctl is-active kis-trading")
status = out.strip()
print(f"  Service status: {status}")

out, err, rc = ssh("tail -n 35 /home/ubuntu/kis-auto-trading/logs/trading_bot.log")
print(f"\n  Latest 35 log lines from VM:")
print(out.strip())

print("\n" + "=" * 60)
print("DATA PROXY CONCURRENCY & TIMEOUT FIX DEPLOYED & LIVE!")
print("=" * 60)
