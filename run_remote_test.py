"""Upload and run the definitive 3-section module audit."""
import subprocess

def scp(src, dst, timeout=30):
    proc = subprocess.Popen(
        ['scp', '-i', 'id_rsa', '-o', 'StrictHostKeyChecking=no', src, dst],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        out, err = proc.communicate(timeout=timeout)
        return proc.returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        return -1

print("Uploading test script...")
rc = scp("remote_module_test.py", "ubuntu@141.148.172.12:/home/ubuntu/kis-auto-trading/remote_module_test.py")
print(f"  rc={rc}")
assert rc == 0, "Upload failed"

print("Running definitive audit (up to 5 min)...")
proc = subprocess.Popen(
    ['ssh', '-i', 'id_rsa', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=15',
     'ubuntu@141.148.172.12',
     'cd ~/kis-auto-trading && source venv/bin/activate && timeout 400 python3 remote_module_test.py 2>&1'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE
)
try:
    out, err = proc.communicate(timeout=420)
    result = out.decode("utf-8", errors="replace")
    with open("audit_stdout.txt", "w", encoding="utf-8") as f:
        f.write(result)
    print(f"Output: {len(result)} chars")
    # Print key lines only
    for line in result.split('\n'):
        s = line.strip()
        if any(x in s for x in ['[PASS]','[FAIL]','[SKIP]','COMPLETE','PASS:','FAIL:','SKIP:']):
            print(s)
    print("DONE!")
except subprocess.TimeoutExpired:
    proc.kill()
    print("TIMEOUT 420s")
