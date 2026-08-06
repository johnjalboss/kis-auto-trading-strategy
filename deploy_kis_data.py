import subprocess

print("Uploading kis_data.py...")
scp_proc = subprocess.Popen(
    ['scp', '-i', 'id_rsa', '-o', 'StrictHostKeyChecking=no', 'kis_data.py', 'ubuntu@141.148.172.12:/home/ubuntu/kis-auto-trading/kis_data.py'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)
out, err = scp_proc.communicate(input="yes\nyes\n")
print("SCP OUT:", out)
print("SCP ERR:", err)
print("SCP RETURN CODE:", scp_proc.returncode)

if scp_proc.returncode == 0:
    print("Restarting service...")
    ssh_proc = subprocess.Popen(
        ['ssh', '-i', 'id_rsa', '-o', 'StrictHostKeyChecking=no', 'ubuntu@141.148.172.12', 'sudo systemctl restart kis-trading'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    out, err = ssh_proc.communicate(input="yes\nyes\n")
    print("SSH OUT:", out)
    print("SSH ERR:", err)
    print("SSH RETURN CODE:", ssh_proc.returncode)
    print("Deployment complete!")
else:
    print("Deployment failed at SCP step.")
