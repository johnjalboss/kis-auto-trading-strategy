"""
find_all_mock_and_fallbacks.py
Scans the entire codebase for hardcoded dummy data, mock dictionaries, and synthetic fallbacks.
"""

import os
import re

PATTERNS = [
    r'mock',
    r'synthetic',
    r'_DEFAULT_[A-Z_]+_DB',
    r'hashlib\.md5',
    r'dummy',
    r'fallback',
    r'sample',
    r'fake'
]

def scan():
    print("=" * 80)
    print("🔍 SCANNING ENTIRE CODEBASE FOR STATIC MOCKS, SYNTHETIC DATA & DUMMY FALLBACKS")
    print("=" * 80)

    py_files = [f for f in os.listdir('.') if f.endswith('.py') and not f.startswith('test_') and f != 'find_all_mock_and_fallbacks.py']
    
    findings = {}

    for fname in py_files:
        try:
            with open(fname, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception:
            continue

        file_matches = []
        for idx, line in enumerate(lines):
            for pat in PATTERNS:
                if re.search(pat, line, re.IGNORECASE):
                    # Filter out purely benign words or comments if needed, but keep broad for strict audit
                    file_matches.append((idx + 1, pat, line.strip()))
                    break

        if file_matches:
            findings[fname] = file_matches

    for fname, matches in findings.items():
        print(f"\n📂 File: {fname} ({len(matches)} occurrences)")
        for line_no, pat, content in matches[:15]:
            print(f"   Line {line_no:4d} [{pat}]: {content[:100]}")

if __name__ == "__main__":
    scan()
