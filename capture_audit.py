import subprocess, sys

if __name__ == "__main__":
    r = subprocess.run(
        [sys.executable, 'local_audit.py'],
        capture_output=True, encoding='utf-8', errors='replace'
    )
    with open('audit_full.txt', 'w', encoding='utf-8') as f:
        f.write(r.stdout)
        if r.stderr:
            f.write("\n--- STDERR ---\n")
            f.write(r.stderr)
    print("Written to audit_full.txt")
    print(r.stdout[-3000:])
