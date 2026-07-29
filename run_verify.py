import subprocess, time

def scp(src, dst, timeout=30):
    proc = subprocess.Popen(
        ['scp', '-i', 'id_rsa', '-o', 'StrictHostKeyChecking=no',
         '-o', 'ConnectTimeout=15', src, dst],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out, err = proc.communicate(timeout=timeout)
    return proc.returncode, out.decode("utf-8", errors="replace"), err.decode("utf-8", errors="replace")

def ssh(cmd, timeout=30):
    proc = subprocess.Popen(
        ['ssh', '-i', 'id_rsa', '-o', 'StrictHostKeyChecking=no',
         '-o', 'ConnectTimeout=15', 'ubuntu@141.148.172.12', cmd],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        out, err = proc.communicate(timeout=timeout)
        return out.decode("utf-8", errors="replace"), err.decode("utf-8", errors="replace"), proc.returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        return "", "TIMEOUT", -1

# Step 1: Launch audit in background on the server
print("Launching audit on server in background...")
out, err, rc = ssh("cd ~/kis-auto-trading && source venv/bin/activate && nohup timeout 150 python3 final_verify.py > /tmp/audit_out.txt 2>&1 &")
print(f"Launch rc={rc}, err={err[:200]}")

# Step 2: Wait for audit to complete
print("Waiting 120s for audit to complete...")
time.sleep(60)
print("60s elapsed, checking if done...")

for i in range(6):
    out, _, _ = ssh("ls -la /tmp/audit_out.txt 2>&1")
    print(f"  [{i+1}/6] {out.strip()}")
    # Check if it has FINAL VERDICT
    out_content, _, _ = ssh("grep -c 'FINAL VERDICT' /tmp/audit_out.txt 2>/dev/null || echo '0'")
    if out_content.strip() != '0':
        print("  Audit completed!")
        break
    time.sleep(15)

# Step 3: Download result
print("\nDownloading audit result...")
rc, out, err = scp('ubuntu@141.148.172.12:/tmp/audit_out.txt', 'audit_out.txt', timeout=30)
print(f"Download rc={rc} err={err[:200]}")
