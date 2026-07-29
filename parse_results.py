import subprocess

proc = subprocess.Popen(
    ['scp', '-i', 'id_rsa', '-o', 'StrictHostKeyChecking=no',
     'ubuntu@141.148.172.12:/tmp/module_audit_result.json', 'module_audit_result.json'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE
)
out, err = proc.communicate(timeout=30)
print(f"rc={proc.returncode}", err.decode("utf-8", errors="replace")[:100])

if proc.returncode == 0:
    import json
    with open('module_audit_result.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"\nPASS ({len(data['PASS'])}): {', '.join(data['PASS'])}")
    print(f"\nNO_ANALYZE ({len(data['NO_ANALYZE'])}): {', '.join(data['NO_ANALYZE'])}")
    print(f"\nFAIL ({len(data['FAIL'])}):")
    for name, reason in data['FAIL']:
        print(f"  - {name}: {reason}")
