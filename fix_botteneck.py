import os

def fix_file(path, target, replacement):
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if target in content:
        new_content = content.replace(target, replacement)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Fixed: {path}")
    else:
        print(f"Target not found in {path}")

# 1. base_adapters.py
fix_file('/home/ubuntu/kis-auto-trading/base_adapters.py', 
    "'deep_verify',", 
    "'deep_verify', 'inspect_', 'diag_', 'all_modules_', 'verify_', 'test_', 'alpha_',")

# 2. indicators.py (if print is at top level)
# (Assuming it might be already fixed or needs specific check)

print("Fixing all modules...")
# Add more specific fixes if needed or just use this script for base_adapters first
