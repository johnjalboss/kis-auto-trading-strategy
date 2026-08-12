import glob, re

files = glob.glob('*.py') + glob.glob('*.txt') + glob.glob('*.sh') + glob.glob('*.json')
ips = set()
for f in files:
    try:
        with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
            content = fp.read()
            matches = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', content)
            for m in matches:
                if not m.startswith('127.') and not m.startswith('0.0.'):
                    ips.add((m, f))
    except Exception:
        pass

print("=== SERVER IP ADDRESSES FOUND IN CODEBASE ===")
for ip, f in ips:
    print(f"IP: {ip} (found in {f})")
