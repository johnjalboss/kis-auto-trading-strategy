import subprocess
import time

KEY = 'id_rsa'
SERVER = 'ubuntu@141.148.172.12'
REMOTE_DIR = '/home/ubuntu/kis-auto-trading'

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
print("DEPLOYING universe.py TO ORACLE VM...")
print("=" * 60)

# 1. SCP universe.py
print("\n[1/4] SCP universe.py to Oracle VM...")
rc, err = scp('universe.py', f'{REMOTE_DIR}/universe.py')
if rc == 0:
    print("  OK  universe.py uploaded")
else:
    print(f"  FAIL universe.py: {err.strip()[:120]}")
    exit(1)

# 2. Clear remote cache & pycache
print("\n[2/4] Clearing remote caches and __pycache__...")
ssh(f"rm -f {REMOTE_DIR}/universe_cache.json")
ssh(f"find {REMOTE_DIR} -name '__pycache__' -type d -exec rm -rf {{}} + 2>/dev/null")
print("  OK caches and pycache cleared")

# 3. Restart kis-trading service
print("\n[3/4] Restarting kis-trading service...")
out, err, rc = ssh("sudo systemctl restart kis-trading")
print(f"  restart rc={rc}")
time.sleep(5)

# Verify service is active
out, err, rc = ssh("systemctl is-active kis-trading")
status = out.strip()
print(f"  Service status: {status}")

# 4. Run refresh_universe.py on VM
print("\n[4/4] Running refresh_universe.py on Oracle VM...")
out, err, rc = ssh(f"cd {REMOTE_DIR} && python3 refresh_universe.py")
print("--- REMOTE DIAGNOSTICS OUTPUT ---")
print(out.strip())
print("---------------------------------")
if err.strip():
    print("--- REMOTE DIAGNOSTICS ERROR ---")
    print(err.strip())
    print("--------------------------------")

out, err, rc = ssh("journalctl -u kis-trading --no-pager -n 8 --output=short")
print(f"\n  Last 8 service log lines:")
for line in out.strip().split('\n'):
    print(f"    {line}")

print("\n" + "=" * 60)
print("DEPLOYMENT & DIAGNOSTICS COMPLETED")
print("=" * 60)
