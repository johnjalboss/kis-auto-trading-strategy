import sys
import os
import pandas as pd
from loguru import logger

# Add current dir to path
sys.path.append(os.getcwd())

from base_adapters import get_available_adapters

def audit_adapters():
    """Verify that all adapters have the required attributes and methods"""
    from base_adapters import get_available_adapters
    import inspect
    adapters = get_available_adapters()
    print(f"Auditing {len(adapters)} adapters...")
    
    issues = []
    for adapter_class in adapters:
        name = adapter_class.__name__
        try:
            # Check for required methods
            if not hasattr(adapter_class, 'analyze'):
                issues.append(f"MISSING_METHOD: {name} lacks analyze()")
            
            # Check for attributes (BaseAnalyzer defaults should handle this now)
            # But we check if they are overridden correctly
            for attr in ['category', 'name', 'is_symbol_dependent']:
                # If it's a property, it might need instantiation to check value, 
                # but hasattr should work on the class if it's a property.
                if not hasattr(adapter_class, attr):
                    issues.append(f"MISSING_ATTR: {name} lacks {attr}")
                
        except Exception as e:
            issues.append(f"AUDIT_FAILURE: {name} - {str(e)}")
            
    if issues:
        print("\n--- AUDIT ISSUES FOUND ---")
        for issue in issues:
            print(f"  [!] {issue}")
    else:
        print("\n--- ALL ADAPTERS PASSED INTEGRITY CHECK ---")
            
    if issues:
        print("\n--- AUDIT ISSUES FOUND ---")
        for issue in issues:
            print(f"  [!] {issue}")
    else:
        print("\n--- ALL ADAPTERS PASSED INTEGRITY CHECK ---")
            
    if issues:
        print("\n--- AUDIT ISSUES FOUND ---")
        for issue in issues:
            print(f"  [!] {issue}")
    else:
        print("\n--- ALL ADAPTERS PASSED INTEGRITY CHECK ---")

if __name__ == "__main__":
    audit_adapters()
