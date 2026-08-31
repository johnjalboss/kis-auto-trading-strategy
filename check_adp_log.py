import subprocess

script = """
import subprocess

# Check log files
res = subprocess.run(['grep', '-i', 'ADP', '/home/ubuntu/kis-auto-trading/trading.log'], capture_output=True, text=True)
if not res.stdout:
    # check other log files
    res2 = subprocess.run(['grep', '-rn', '-i', 'ADP', '/home/ubuntu/kis-auto-trading/logs/'], capture_output=True, text=True)
    print("Logs dir grep:")
    print(res2.stdout[:3000])
else:
    print("trading.log grep:")
    print(res.stdout[:3000])

# Also check journalctl for kis service around Aug 20
res3 = subprocess.run(['journalctl', '-u', 'kis-trading', '--since', '2026-08-19 23:50:00', '--until', '2026-08-20 01:00:00', '--no-pager'], capture_output=True, text=True)
print("Journalctl around ADP buy:")
print(res3.stdout[:4000])
"""

res = subprocess.run(
    ['ssh', '-i', 'id_rsa', '-o', 'StrictHostKeyChecking=no', 'ubuntu@141.148.172.12', 'python3'],
    input=script,
    capture_output=True,
    text=True,
    encoding='utf-8',
    errors='replace'
)

with open('vps_adp_log.txt', 'w', encoding='utf-8') as f:
    f.write('STDOUT:\n' + res.stdout + '\nSTDERR:\n' + res.stderr)

print("Saved to vps_adp_log.txt successfully")
