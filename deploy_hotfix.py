import subprocess

def scp(src, dst):
    subprocess.run(['scp', '-i', 'id_rsa', '-o', 'StrictHostKeyChecking=no', src, dst], check=True)

def ssh(cmd):
    subprocess.run(['ssh', '-i', 'id_rsa', '-o', 'StrictHostKeyChecking=no', 'ubuntu@141.148.172.12', cmd], check=True)

try:
    print("Uploading orchestrator.py hotfix...")
    scp("orchestrator.py", "ubuntu@141.148.172.12:/home/ubuntu/kis-auto-trading/")
    print("Restarting service one final time to load dynamic reloading logic...")
    ssh("sudo systemctl restart kis-trading")
    print("Orchestrator hotfix deployed successfully!")
except Exception as e:
    print("Deploy failed:", e)
