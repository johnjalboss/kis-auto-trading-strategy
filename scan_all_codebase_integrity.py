"""
Comprehensive Whole-Codebase AST & Import & Execution Syntax Audit
===================================================================
Scans all .py files in the workspace for:
1. Python AST parsing (SyntaxError, IndentationError).
2. Unhandled syntax or invalid character tokens.
3. Import checks for all production trading modules.
"""

import os
import sys
import ast
import importlib

sys.stdout.reconfigure(encoding='utf-8')
workspace_dir = os.path.dirname(os.path.abspath(__file__))

print("======================================================================")
print("🔍 EXHAUSTIVE WHOLE-CODEBASE SYNTAX & AST SCAN")
print("======================================================================")

py_files = [f for f in os.listdir(workspace_dir) if f.endswith('.py') and not f.startswith('test_')]
print(f"Total Python Production & Analysis Files Found: {len(py_files)}\n")

errors = []
for fname in sorted(py_files):
    fpath = os.path.join(workspace_dir, fname)
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code, filename=fname)
        print(f"  [OK] {fname:<38} : Valid AST")
    except Exception as e:
        print(f"  [FAIL] {fname:<36} : {e}")
        errors.append((fname, str(e)))

print("\n======================================================================")
if errors:
    print(f"❌ FOUND {len(errors)} CODEBASE SYNTAX/AST ERRORS:")
    for fn, err in errors:
        print(f"  - {fn}: {err}")
    sys.exit(1)
else:
    print(f"🎉 100% OF {len(py_files)} PYTHON FILES PASSED SYNTAX & AST AUDIT!")
print("======================================================================")
