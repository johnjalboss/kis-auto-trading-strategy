"""
Deploy v1.1.7 — Core Quant Engine Fixes
=========================================
1. composite_signal.py: Added get_signal() module-level function with 30-min cache
2. strategy.py:         Fixed comp_engine.get_signal() → module-level get_signal() 
3. data_proxy.py:       Removed dead code, increased yfinance rate limit 60→120
4. screener.py:         Parallelized _gather_squeeze_candidates (16 workers, 300 cap)
5. config.py:           Added SCREENED_MIN_SCORE, fixed DAILY_STOP_LOSS 3%→5%, 
                        CONSECUTIVE_LOSS_LIMIT 3→4
"""
import subprocess
import time

KEY = 'id_rsa'
SERVER = 'ubuntu@141.148.172.12'
REMOTE_DIR = '/home/ubuntu/kis-auto-trading'

CHANGED_FILES = [
    'composite_signal.py',   # CRITICAL: Added get_signal() with 30-min cache
    'strategy.py',           # CRITICAL: Fixed AttributeError on comp_engine.get_signal()
    'data_proxy.py',         # BUG: Removed unreachable dead code, rate limit 60→120
    'screener.py',           # PERF: Parallelized squeeze scan (300 stocks, 16 workers)
    'config.py',             # FIX: Added missing SCREENED_MIN_SCORE, relaxed stop params
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
print("DEPLOY v1.1.7 -- Core Quant Engine Fixes")
print("=" * 60)

# 1. Upload changed files
print("\n[1/3] Uploading changed files...")
ok = 0
fail = 0
for f in CHANGED_FILES:
    rc, err = scp(f, f'{REMOTE_DIR}/{f}')
    if rc == 0:
        print(f"  OK  {f}")
        ok += 1
    else:
        print(f"  FAIL {f}: {err.strip()[:80]}")
        fail += 1

print(f"\n  Uploaded: {ok}  |  Failed: {fail}")

if fail > 0:
    print("\nWARNING: Some files failed to upload. Aborting restart.")
    exit(1)

# 2. Clear stale pycache
print("\n[2/3] Clearing stale __pycache__...")
out, err, rc = ssh("find /home/ubuntu/kis-auto-trading -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null; echo DONE")
print(f"  {out.strip()}")

# 3. Restart service
print("\n[3/3] Restarting kis-trading service...")
out, err, rc = ssh("sudo systemctl restart kis-trading")
print(f"  restart rc={rc}")

time.sleep(6)
out, err, rc = ssh("systemctl is-active kis-trading")
status = out.strip()
print(f"  Service status: {status}")

out, err, rc = ssh("journalctl -u kis-trading --no-pager -n 8 --output=short")
print(f"\n  Last 8 log lines:")
for line in out.strip().split('\n'):
    print(f"    {line}")

print("\n" + "=" * 60)
if status == 'active':
    print("SUCCESS: v1.1.7 deployed -- Oracle VM updated and RUNNING")
else:
    print(f"WARNING: Service status '{status}' - check server logs")
print("=" * 60)
