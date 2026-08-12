import os, glob

files = glob.glob('*.py')
missing = []
for f in files:
    with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
        content = fp.read()
        if 'config.' in content and 'import config' not in content and 'from config import' not in content:
            missing.append(f)

print("Files missing 'import config':", missing)
