import os, glob, re

files = glob.glob('*.py')
hardcoded_patterns = [
    (r'bp\s*=\s*9650', 'Hardcoded BP 9650'),
    (r'balance\s*=\s*100', 'Hardcoded Balance 100'),
    (r'entry_price\s*=\s*100', 'Hardcoded Entry 100'),
    (r'price\s*=\s*100\.0', 'Hardcoded Price 100.0'),
    (r'10000\.0', 'Hardcoded 10000.0'),
]

found = []
for f in files:
    with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
        for line_no, line in enumerate(fp, 1):
            for pattern, desc in hardcoded_patterns:
                if re.search(pattern, line):
                    found.append((f, line_no, desc, line.strip()))

print(f"=== FOUND {len(found)} HARDCODED DUMMY VALUES ===")
for item in found:
    print(f"{item[0]}:{item[1]} - {item[2]} -> {item[3]}")
