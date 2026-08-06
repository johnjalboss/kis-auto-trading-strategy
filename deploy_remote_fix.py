import subprocess
import time

SERVER = "ubuntu@141.148.172.12"
KEY = "id_rsa"
REMOTE_DIR = "/home/ubuntu/kis-auto-trading"

def run_cmd(cmd_list):
    proc = subprocess.Popen(
        cmd_list,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out, err = proc.communicate(timeout=60)
    return proc.returncode, out.decode("utf-8", errors="replace"), err.decode("utf-8", errors="replace")

files_to_deploy = [
    "base_adapters.py",
    "drawdown_controller.py",
    "orchestrator.py",
    "risk_manager.py",
    "strategy.py",
    "database.py",
    "reporter.py",
    "drawdown_state.json"
]

print(f"🚀 Starting deployment to {SERVER}...")

for filename in files_to_deploy:
    print(f"  📤 Uploading {filename}...")
    rc, out, err = run_cmd(['scp', '-i', KEY, '-o', 'StrictHostKeyChecking=no', filename, f"{SERVER}:{REMOTE_DIR}/{filename}"])
    if rc == 0:
        print(f"    ✅ {filename} uploaded.")
    else:
        print(f"    ❌ FAILED to upload {filename}: {err}")
        exit(1)

print("  🔄 Restarting kis-trading service...")
rc, out, err = run_cmd(['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', SERVER, 'sudo systemctl restart kis-trading'])
if rc == 0:
    print("    ✅ Service restarted.")
else:
    print(f"    ❌ FAILED to restart service: {err}")
    exit(1)

print("  🔍 Verifying service status...")
time.sleep(5)
rc, out, err = run_cmd(['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', SERVER, 'systemctl is-active kis-trading'])
print(f"    Service status: {out.strip()}")

print("\n✨ Deployment Complete!")
