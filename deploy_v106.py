"""
v1.0.6 Targeted Hotfix Deployer
================================
Only deploys the specific files changed in v1.0.6 to avoid SCP timeout.
"""
import subprocess
import time

REMOTE_USER = "ubuntu"
REMOTE_HOST = "141.148.172.12"
REMOTE_DIR = "/home/ubuntu/kis-auto-trading"
SSH_KEY = "id_rsa"

# Only the files that changed in v1.0.6
V106_CHANGED_FILES = [
    "strategy.py",
    "orchestrator.py",
]

def scp(local, remote_path):
    """SCP a single file with timeout."""
    proc = subprocess.Popen(
        ['scp', '-i', SSH_KEY,
         '-o', 'StrictHostKeyChecking=no',
         '-o', 'ConnectTimeout=15',
         local, f'{REMOTE_USER}@{REMOTE_HOST}:{remote_path}'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        out, err = proc.communicate(timeout=90)
        return proc.returncode, err.decode('utf-8', errors='replace')
    except subprocess.TimeoutExpired:
        proc.kill()
        return 1, "TIMEOUT after 90s"

def ssh(cmd):
    """Run SSH command."""
    proc = subprocess.Popen(
        ['ssh', '-i', SSH_KEY,
         '-o', 'StrictHostKeyChecking=no',
         '-o', 'ConnectTimeout=15',
         f'{REMOTE_USER}@{REMOTE_HOST}', cmd],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        out, err = proc.communicate(timeout=60)
        return out.decode('utf-8', errors='replace'), err.decode('utf-8', errors='replace'), proc.returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        return "", "TIMEOUT", 1

print("=" * 50)
print("v1.0.6 Targeted Hotfix Deploy")
print("=" * 50)

# 1. Upload changed files only
print("\n[1] Uploading changed files...")
success = 0
for f in V106_CHANGED_FILES:
    remote = f"{REMOTE_DIR}/{f}"
    rc, err = scp(f, remote)
    status = "OK" if rc == 0 else f"FAIL: {err.strip()[:80]}"
    print(f"  {f} -> {status}")
    if rc == 0:
        success += 1

print(f"\n  {success}/{len(V106_CHANGED_FILES)} files uploaded successfully.")

# 2. Clear pycache
print("\n[2] Clearing __pycache__...")
out, err, rc = ssh(f"find {REMOTE_DIR} -name '__pycache__' -type d -exec rm -rf {{}} + 2>/dev/null; echo done")
print(f"  {out.strip()}")

# 3. Restart service
print("\n[3] Restarting kis-trading service...")
out, err, rc = ssh("sudo systemctl restart kis-trading")
print(f"  restart rc={rc} {err.strip()[:80]}")

# Wait for service to come up
time.sleep(6)

# 4. Verify service is active
print("\n[4] Checking service status...")
out, err, rc = ssh("systemctl is-active kis-trading")
status = out.strip()
print(f"  Service: {status}")

out2, _, _ = ssh("systemctl status kis-trading --no-pager -n 5")
for line in out2.strip().splitlines()[:8]:
    print(f"  {line}")

if status == "active":
    print("\n✅ v1.0.6 deployed and service is ACTIVE!")
else:
    print(f"\n⚠️  Service status: {status} - check server logs")

print("=" * 50)
