import subprocess

lines = []

def ssh_run(cmd):
    proc = subprocess.Popen(
        ['ssh', '-i', 'id_rsa', 
         '-o', 'StrictHostKeyChecking=no',
         '-o', 'ConnectTimeout=15',
         'ubuntu@141.148.172.12', cmd],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        out, err = proc.communicate(timeout=25)
        return out.decode("utf-8", errors="replace").strip(), proc.returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        return "TIMEOUT", -1

if __name__ == "__main__":
    # Find the most recently modified log file
    out, rc = ssh_run("ls -t /home/ubuntu/kis-auto-trading/*.log 2>&1 | head -1")
    print(f"Newest log: {out}, rc={rc}")

    if out and not out.startswith(('TIMEOUT', 'ls:')):
        # Download it
        proc = subprocess.Popen(
            ['scp', '-i', 'id_rsa', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=15',
             f'ubuntu@141.148.172.12:{out}', 'session_log.txt'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        try:
            sout, serr = proc.communicate(timeout=30)
            print(f"SCP rc={proc.returncode}")
            print(serr.decode("utf-8", errors="replace")[:200])
        except subprocess.TimeoutExpired:
            proc.kill()
            print("SCP TIMEOUT")
