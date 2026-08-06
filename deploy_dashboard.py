import subprocess

SERVER = "ubuntu@141.148.172.12"
KEY = "id_rsa"
REMOTE_DIR = "/home/ubuntu/kis-auto-trading"

print("Uploading fetch_dashboard_data.py...")
cmd = ['scp', '-i', KEY, '-o', 'StrictHostKeyChecking=no', 'fetch_dashboard_data.py', f"{SERVER}:{REMOTE_DIR}/fetch_dashboard_data.py"]
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
out, err = proc.communicate()

if proc.returncode == 0:
    print("Dashboard data script deployed successfully.")
else:
    print(f"Failed to deploy: {err.decode('utf-8', errors='replace')}")
