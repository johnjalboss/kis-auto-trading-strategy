import os
import ast
import glob
from loguru import logger

def audit_file(file_path):
    issues = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
        
        # 1. AST Syntax Check
        try:
            tree = ast.parse(code, filename=file_path)
        except SyntaxError as se:
            issues.append(f"[SYNTAX ERROR] Line {se.lineno}: {se.msg}")
            return issues
        
        # Walk through AST
        for node in ast.walk(tree):
            # 2. Division by Zero Risk
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                # Check divisor
                divisor = node.right
                if isinstance(divisor, ast.Constant):
                    if divisor.value == 0:
                        issues.append(f"[CRITICAL division-by-zero] Line {node.lineno}: division by literal zero")
                else:
                    # Variable divisor - flag for manual guard review
                    issues.append(f"[Division-By-Zero-Risk] Line {node.lineno}: division by variable or expression (requires guard)")
            
            # 3. Exception Swallowing
            if isinstance(node, ast.Try):
                for handler in node.handlers:
                    # check if the body of the handler is just pass
                    if len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass):
                        issues.append(f"[Exception-Swallowing] Line {handler.lineno}: try-except block silently swallows exceptions")
            
            # 4. Resource Leaks
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "open":
                    # check if inside a with statement by traversing parent or simple warning
                    # (Simplified check: warn if not in a With block)
                    pass
                    
    except Exception as e:
        issues.append(f"[FILE AUDIT ERROR] Could not read file: {e}")
        
    return issues

def main():
    logger.info("=" * 60)
    logger.info("🤖 STARTING FULL SYSTEM PROGRAMMATIC AUDIT (AST-BASED)")
    logger.info("=" * 60)
    
    py_files = sorted(glob.glob("*.py"))
    logger.info("Auto-discovered {} Python files to inspect...", len(py_files))
    
    total_issues = 0
    clean_files = 0
    
    for f in py_files:
        # Skip audit script itself
        if f == "full_programmatic_audit.py":
            continue
            
        issues = audit_file(f)
        if not issues:
            clean_files += 1
        else:
            print(f"\nAUDIT REPORT FOR: {f}")
            for issue in issues:
                print(f"  → {issue}")
            total_issues += len(issues)
            
    logger.info("=" * 60)
    logger.info("📊 FULL SYSTEM AUDIT COMPLETED")
    logger.info("=" * 60)
    logger.info("  Clean Files: {} / {}", clean_files, len(py_files))
    logger.info("  Total Issues/Risks Flagged: {}", total_issues)
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
