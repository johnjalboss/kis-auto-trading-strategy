"""Upload screener.py and restart kis-trading service."""
import subprocess, time

SERVER = "ubuntu@141.148.172.12"
KEY = r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading\id_rsa"
REMOTE_DIR = "/home/ubuntu/kis-auto-trading"

FILES = ["screener.py"]

for fname in FILES:
    for attempt in range(3):
        try:
            proc = subprocess.Popen(
                ['scp', '-i', KEY, '-o', 'StrictHostKeyChecking=no',
                 '-o', 'ConnectTimeout=20', fname, f"{SERVER}:{REMOTE_DIR}/{fname}"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            out, err = proc.communicate(timeout=90)
            rc = proc.returncode
            print(f"  [{attempt+1}/3] {fname}: rc={rc} {err.decode('utf-8','replace')[:100].strip()}")
            if rc == 0:
                break
        except subprocess.TimeoutExpired:
            proc.kill()
            print(f"  [{attempt+1}/3] {fname}: TIMEOUT, retrying...")
            time.sleep(10)
    else:
        print(f"  FAILED after 3 attempts: {fname}")

# Restart
print("Restarting service...")
try:
    proc = subprocess.Popen(
        ['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=20',
         SERVER, 'sudo systemctl restart kis-trading && sleep 3 && systemctl is-active kis-trading'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out, err = proc.communicate(timeout=90)
    print(f"  restart: {out.decode('utf-8','replace').strip()}")
except subprocess.TimeoutExpired:
    proc.kill()
    print("  restart: TIMEOUT")

print("Done!")
