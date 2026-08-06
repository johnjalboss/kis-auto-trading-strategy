import subprocess
import time

SERVER = "ubuntu@141.148.172.12"
KEY = "id_rsa"
REMOTE_DIR = "/home/ubuntu/kis-auto-trading"
FILES = ["config.py", "indicators.py", "screener.py", "strategy.py", "orchestrator.py", "telegram_commander.py"]

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

print(f"Deploying strategy files to {SERVER}...")

for f in FILES:
    print(f"  Uploading {f}...")
    rc, out, err = run_cmd(['scp', '-i', KEY, '-o', 'StrictHostKeyChecking=no', f, f"{SERVER}:{REMOTE_DIR}/{f}"])
    if rc != 0:
        print(f"  FAILED to upload {f}: {err}")
        exit(1)

print("  Restarting kis-trading service...")
rc, out, err = run_cmd(['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', SERVER, 'sudo systemctl restart kis-trading'])
if rc == 0:
    print("  -> Service restarted.")
else:
    print(f"  FAILED to restart service: {err}")

print("Checking service status...")
time.sleep(3)
rc, out, err = run_cmd(['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', SERVER, 'systemctl is-active kis-trading'])
print(f"  Service status: {out.strip()}")
print("Done!")
