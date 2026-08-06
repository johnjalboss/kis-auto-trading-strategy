import subprocess
import os

# Oracle VPS SSH Connection Details
IP = "141.148.172.12"
USER = "ubuntu"
KEY_FILE = "id_rsa"

def scp(src, dst):
    proc = subprocess.Popen(
        ['scp', '-i', KEY_FILE, '-o', 'StrictHostKeyChecking=no', src, dst],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out, err = proc.communicate(input=b"yes\n", timeout=120)
    return proc.returncode, err.decode("utf-8", errors="replace")

def ssh(cmd):
    proc = subprocess.Popen(
        ['ssh', '-i', KEY_FILE, '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=15',
         f'{USER}@{IP}', cmd],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out, err = proc.communicate(input=b"yes\n", timeout=120)
    return out.decode("utf-8", errors="replace"), err.decode("utf-8", errors="replace"), proc.returncode

def main():
    # 1. Create directory on VPS
    print("1. Creating remote theme tracker directory on Oracle VPS...")
    ssh("mkdir -p /home/ubuntu/us-theme-tracker")

    # 2. Upload files
    print("2. Uploading theme tracker files...")
    tracker_src = r"C:\Users\wngud\.gemini\antigravity\scratch\us-theme-tracker"
    files_to_deploy = ["app.py", "theme_db.json", "update_signals_batch.py", "us_stocks_data.db"]

    for f in files_to_deploy:
        src_file = os.path.join(tracker_src, f)
        dst_file = f"/home/ubuntu/us-theme-tracker/{f}"
        rc, err = scp(src_file, f'{USER}@{IP}:{dst_file}')
        if rc == 0:
            print(f"  Successfully uploaded {f}")
        else:
            print(f"  Failed to upload {f}: {err.strip()[:100]}")

    # 3. Install packages
    print("3. Installing required python packages on Oracle VPS...")
    out, err, rc = ssh("sudo pip3 install pandas numpy yfinance --break-system-packages")
    print(f"  pip install rc={rc}")

    # 4. Run initial compilation on VPS
    print("4. Executing initial batch signal calculations on VPS (Asynchronously)...")
    out, err, rc = ssh("nohup python3 /home/ubuntu/us-theme-tracker/update_signals_batch.py > /home/ubuntu/us-theme-tracker/init.log 2>&1 &")
    if rc == 0:
        print("  Background batch process started successfully.")
    else:
        print(f"  Failed to start background process: exit code {rc}")
        print(f"  Stderr: {err.strip()[:300]}")

    # 5. Configure crontab scheduler on VPS
    print("5. Configuring 15-minute crontab scheduler on VPS...")
    cron_out, _, _ = ssh("crontab -l")
    # Clean up empty lines and headers
    cron_jobs = [line.strip() for line in cron_out.split("\n") if line.strip() and not line.strip().startswith("#")]
    
    target_job = "*/15 * * * * cd /home/ubuntu/us-theme-tracker && /usr/bin/python3 update_signals_batch.py >> /home/ubuntu/us-theme-tracker/batch.log 2>&1"
    
    # Check if already exists
    exists = False
    for job in cron_jobs:
        if "update_signals_batch.py" in job:
            exists = True
            break
            
    if not exists:
        cron_jobs.append(target_job)
        new_cron = "\n".join(cron_jobs) + "\n"
        # Escape quotes for echo
        escaped_cron = new_cron.replace("'", "'\\''")
        ssh(f"echo '{escaped_cron}' | crontab -")
        print("  Crontab scheduler successfully configured!")
    else:
        print("  Crontab scheduler already exists.")

    print("\nTheme tracker server components deployment complete!")

if __name__ == "__main__":
    main()
