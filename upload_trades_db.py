import subprocess

print("Uploading local trades.db (with 12 historical trades & daily_stats) to VPS...")
cmd = [
    "scp", "-i", "id_rsa", "-o", "StrictHostKeyChecking=no",
    "trades.db", "ubuntu@141.148.172.12:/home/ubuntu/kis-auto-trading/trades.db"
]
res = subprocess.run(cmd, capture_output=True, text=True)
print("SCP Output:", res.stdout)
if res.stderr:
    print("SCP Stderr:", res.stderr)

print("\nSyncing VPS DB positions with live KIS API...")
sync_cmd = [
    "ssh", "-i", "id_rsa", "-o", "StrictHostKeyChecking=no",
    "ubuntu@141.148.172.12", "python3 /home/ubuntu/kis-auto-trading/sync_vps_db_with_kis.py"
]
s_res = subprocess.run(sync_cmd, capture_output=True, text=True)
print("Sync Output:", s_res.stdout)
if s_res.stderr:
    print("Sync Stderr:", s_res.stderr)
