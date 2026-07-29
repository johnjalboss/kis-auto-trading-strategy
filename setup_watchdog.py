import subprocess, time

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

def scp(src, dst, timeout=60):
    proc = subprocess.Popen(
        ['scp', '-i', 'id_rsa', '-o', 'StrictHostKeyChecking=no', src, dst],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        out, err = proc.communicate(timeout=timeout)
        return proc.returncode, err.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        proc.kill()
        return -1, "TIMEOUT"

# 1. Upload watchdog.py
print("1. Uploading watchdog.py...")
rc, err = scp('watchdog.py', 'ubuntu@141.148.172.12:/home/ubuntu/kis-auto-trading/watchdog.py')
print(f"   rc={rc} {err.strip()[:100]}")

# 2. Show current service exec
print("\n2. Current ExecStart:")
out, _ = ssh("grep ExecStart /etc/systemd/system/kis-trading.service")
print(f"   {out.strip()}")

# 3. Update systemd to use watchdog.py
print("\n3. Updating service to use watchdog.py...")
# The service currently runs main_autonomous.py or main.py directly
# We need to switch ExecStart to watchdog.py
out, err = ssh(
    "sudo sed -i 's|ExecStart=.*main.*\\.py|ExecStart=/home/ubuntu/kis-auto-trading/venv/bin/python /home/ubuntu/kis-auto-trading/watchdog.py|g' "
    "/etc/systemd/system/kis-trading.service && echo 'Updated'"
)
print(f"   {out.strip()}")

# 4. Verify the change
print("\n4. Verify ExecStart after update:")
out, _ = ssh("grep ExecStart /etc/systemd/system/kis-trading.service")
print(f"   {out.strip()}")

# 5. Reload and restart
print("\n5. Reload systemd and restart service...")
out, err = ssh("sudo systemctl daemon-reload && sudo systemctl restart kis-trading && sleep 3 && systemctl is-active kis-trading")
print(f"   {out.strip()}")

print("\nDone! Telegram alerts will now be sent on crash/start.")
