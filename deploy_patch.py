import subprocess
import time

SERVER = "ubuntu@141.148.172.12"
KEY = "id_rsa"
REMOTE_DIR = "/home/ubuntu/kis-auto-trading"

def run_cmd(cmd_list, timeout=60):
    proc = subprocess.Popen(
        cmd_list,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        out, err = proc.communicate(timeout=timeout)
        return proc.returncode, out.decode("utf-8", errors="replace"), err.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        proc.kill()
        return -1, "", "TIMEOUT"

print(f"Deploying patch to {SERVER}...")

# 1. Upload orchestrator.py & smart_order.py
print("  [1/3] Uploading orchestrator.py...")
rc, out, err = run_cmd(['scp', '-i', KEY, '-o', 'StrictHostKeyChecking=no', 'orchestrator.py', f"{SERVER}:{REMOTE_DIR}/orchestrator.py"])
if rc != 0:
    print(f"  FAILED to upload orchestrator.py: {err}")
    exit(1)

print("  [2/3] Uploading smart_order.py...")
rc, out, err = run_cmd(['scp', '-i', KEY, '-o', 'StrictHostKeyChecking=no', 'smart_order.py', f"{SERVER}:{REMOTE_DIR}/smart_order.py"])
if rc != 0:
    print(f"  FAILED to upload smart_order.py: {err}")
    exit(1)


# 3. Restart service
print("  [3/3] Restarting kis-trading service...")
rc, out, err = run_cmd(['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', SERVER, 'sudo systemctl restart kis-trading'])
if rc == 0:
    print("  -> Service restarted.")
else:
    print(f"  FAILED to restart service: {err}")


# 3. Check status
print("Checking service status...")
time.sleep(5)
rc, out, err = run_cmd(['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', SERVER, 'systemctl is-active kis-trading'])
print(f"  Service status: {out.strip()}")

print("Done!")
