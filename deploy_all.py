import subprocess

def scp(src, dst):
    proc = subprocess.Popen(
        ['scp', '-i', 'id_rsa', '-o', 'StrictHostKeyChecking=no', src, dst],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out, err = proc.communicate(input=b"yes\n", timeout=60)
    return proc.returncode, err.decode("utf-8", errors="replace")

def ssh(cmd):
    proc = subprocess.Popen(
        ['ssh', '-i', 'id_rsa', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=15',
         'ubuntu@141.148.172.12', cmd],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out, err = proc.communicate(input=b"yes\n", timeout=60)
    return out.decode("utf-8", errors="replace"), err.decode("utf-8", errors="replace"), proc.returncode

import os
import glob

# Automatically discover all .py files in the current directory
py_files = [f for f in glob.glob("*.py") if f not in ["test.py", "sandbox.py"]]
files = [(f, f"/home/ubuntu/kis-auto-trading/{f}") for f in py_files]

for local, remote in files:
    rc, err = scp(local, f'ubuntu@141.148.172.12:{remote}')
    print(f"  {local} -> rc={rc} {err.strip()[:100]}")

print("Installing dependencies...")
ssh("sudo pip3 install sqlalchemy python-telegram-bot --break-system-packages")

print("Cleaning up stale code...")
ssh("find /home/ubuntu/.local/lib/python3.10/site-packages/ -name 'strategy.pyc' -delete")
ssh("find /home/ubuntu/kis-auto-trading/ -name '__pycache__' -type d -exec rm -rf {} +")

print("Restarting service...")
out, err, rc = ssh("sudo systemctl restart kis-trading")
print(f"  restart rc={rc} err={err.strip()[:100]}")

import time; time.sleep(5)
out, err, rc = ssh("systemctl is-active kis-trading")
print(f"  service status: {out.strip()}")

print("Done - all patched files deployed!")
