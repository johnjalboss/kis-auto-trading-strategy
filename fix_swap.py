import subprocess

def ssh(cmd, timeout=30):
    proc = subprocess.Popen(
        ['ssh', '-i', 'id_rsa', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=15',
         'ubuntu@141.148.172.12', cmd],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        out, err = proc.communicate(timeout=timeout)
        return out.decode("utf-8", errors="replace"), err.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        proc.kill()
        return "TIMEOUT", ""

print("===1. Find swapfile location===")
out, _ = ssh("swapon --show --noheadings 2>/dev/null; ls -lh /swapfile /swap.img 2>/dev/null")
print(out.strip())

print("\n===2. Add swap to /etc/fstab if not already there===")
out, err = ssh(
    "grep -q swapfile /etc/fstab && echo 'already in fstab' || "
    "(echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab && echo 'added to fstab')"
)
print(out.strip())

print("\n===3. Verify fstab===")
out, _ = ssh("grep swap /etc/fstab")
print(out.strip())

print("\n===4. Current memory===")
out, _ = ssh("free -h")
print(out.strip())

print("\n===5. Check composite_signal max_workers===")
out, _ = ssh("grep -n 'max_workers' /home/ubuntu/kis-auto-trading/composite_signal.py | head -5")
print(out.strip())
