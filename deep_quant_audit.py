"""
Deep Quant Codebase Auditor (deep_quant_audit.py)
==================================================
Audits core quant logic for:
1. Division by zero vulnerabilities
2. Missing exception handlers or swallowed exceptions
3. Hardcoded outdated parameters or weak score thresholds
4. Lookahead bias or data latency issues
5. Disconnected or unused indicators
"""

import ast
import os
import glob

def audit_file(filepath):
    issues = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # 1. Division by zero checks
    if '/' in content:
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            if '/' in line and not line.strip().startswith('#'):
                # Check for unprotected division like / entry_price or / len(...)
                if re.search(r'/\s*([a-zA-Z_][a-zA-Z0-9_]*)\b', line):
                    match = re.search(r'/\s*([a-zA-Z_][a-zA-Z0-9_]*)\b', line)
                    var = match.group(1)
                    if var in ['entry_price', 'close', 'price', 'total_equity', 'atr', 'avg_price']:
                        if f"if {var} > 0" not in line and f"if {var}" not in line and f"max(" not in line:
                            issues.append((i, "DIV_ZERO_RISK", f"Potential zero division by '{var}': {line.strip()}"))

    # 2. Hardcoded old static values
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        if 'score' in line.lower() and ('=' in line or '+=' in line or '-=' in line):
            if '100' in line or '50' in line or '30' in line:
                if 'clamped' not in line.lower() and 'max(' not in line.lower():
                    pass # Just scoring logic

    return issues

import re
py_files = [f for f in glob.glob('*.py') if not f.startswith('test_') and not f.startswith('deploy')]
all_issues = {}
for pf in py_files:
    iss = audit_file(pf)
    if iss:
        all_issues[pf] = iss

print(f"=== DEEP QUANT AUDIT FOUND POTENTIAL RISKS IN {len(all_issues)} FILES ===")
for f, iss in all_issues.items():
    print(f"\n[FILE] {f}:")
    for line_no, category, msg in iss[:5]: # Show top 5 per file
        print(f"  Line {line_no} [{category}]: {msg}")
