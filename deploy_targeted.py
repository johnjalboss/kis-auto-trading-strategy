"""
Targeted deploy: only upload the files that were actually changed/fixed.
Much faster than deploy_all.py which uploads ~400 files.
"""
import subprocess
import time

KEY = 'id_rsa'
SERVER = 'ubuntu@141.148.172.12'
REMOTE_DIR = '/home/ubuntu/kis-auto-trading'

CHANGED_FILES = [
    'config.py',
    'strategy.py'
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
print("TARGETED DEPLOY v1.1.1 -- Critical Fixes Only")
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

# 2. Clear stale pycache
print("\n[2/3] Clearing stale __pycache__...")
out, err, rc = ssh("find /home/ubuntu/kis-auto-trading -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null; echo DONE")
print(f"  {out.strip()}")

# 3. Restart service
print("\n[3/3] Restarting kis-trading service...")
out, err, rc = ssh("sudo systemctl restart kis-trading")
print(f"  restart rc={rc}")

time.sleep(5)
out, err, rc = ssh("systemctl is-active kis-trading")
status = out.strip()
print(f"  Service status: {status}")

out, err, rc = ssh("journalctl -u kis-trading --no-pager -n 5 --output=short")
print(f"\n  Last 5 log lines:")
for line in out.strip().split('\n'):
    print(f"    {line}")

print("\n" + "=" * 60)
if status == 'active':
    print("SUCCESS: Oracle VM updated and service is RUNNING")
else:
    print(f"WARNING: Service status is '{status}' - check server logs")
print("=" * 60)
