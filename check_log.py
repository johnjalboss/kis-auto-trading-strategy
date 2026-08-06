import subprocess

proc = subprocess.Popen(
    ['ssh', '-i', 'id_rsa', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=15',
     'ubuntu@141.148.172.12',
     'ls /home/ubuntu/kis-auto-trading/*.py | wc -l; echo "---"; ls /home/ubuntu/kis-auto-trading/*.py | xargs -I{} basename {} .py | sort'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE
)
try:
    out, err = proc.communicate(timeout=20)
    print(out.decode("utf-8", errors="replace"))
except subprocess.TimeoutExpired:
    proc.kill()
    print("TIMEOUT")
