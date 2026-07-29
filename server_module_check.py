import sys
import os
import pprint
from loguru import logger

# Add current dir to path
sys.path.append(os.getcwd())

try:
    from base_adapters import get_adapter_report, get_available_adapters
    from composite_signal import get_composite_engine
    
    print("\n" + "="*60)
    print("### SYSTEM MODULE AUDIT ###")
    print("="*60)
    
    report = get_adapter_report()
    print(f"\nTotal Adapters Found: {report['total']}")
    
    print("\nCategory Breakdown:")
    pprint.pprint(report['by_category'])
    
    print("\n--- Testing Engine Initialization ---")
    engine = get_composite_engine()
    print(f"Engine Analyzers Categories: {list(engine.analyzers.keys())}")
    for cat, mods in engine.analyzers.items():
        print(f"  [{cat.upper()}]: {len(mods)} modules loaded")

    print("\n" + "="*60)
    
except Exception as e:
    print(f"AUDIT FAILED: {e}")
    import traceback
    traceback.print_exc()
