"""Deploy sector_fund_flow.py and verify."""
import subprocess

SERVER = "ubuntu@141.148.172.12"
KEY = "id_rsa"
REMOTE = "/home/ubuntu/kis-auto-trading"

def scp(src, dst, timeout=30):
    proc = subprocess.Popen(
        ['scp', '-i', KEY, '-o', 'StrictHostKeyChecking=no', src, dst],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        out, err = proc.communicate(timeout=timeout)
        return proc.returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        return -1

def ssh(cmd, timeout=20):
    proc = subprocess.Popen(
        ['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=15',
         SERVER, cmd],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        out, err = proc.communicate(timeout=timeout)
        return out.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        proc.kill()
        return "TIMEOUT"

rc = scp("sector_fund_flow.py", f"{SERVER}:{REMOTE}/sector_fund_flow.py")
print(f"Upload: {'OK' if rc == 0 else 'FAIL'}")

out = ssh(f"cd {REMOTE} && source venv/bin/activate && python3 -c \"import sector_fund_flow; print('IMPORT OK')\" 2>&1")
print(f"Import check: {out.strip()}")

out = ssh("sudo systemctl restart kis-trading && sleep 2 && systemctl is-active kis-trading")
print(f"Service: {out.strip()}")
