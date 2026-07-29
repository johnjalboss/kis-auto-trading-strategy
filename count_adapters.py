"""Count adapters after rewrite"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

from base_adapters import get_available_adapters, get_adapter_report

adapters = get_available_adapters()
report = get_adapter_report()

print(f"TOTAL ADAPTERS: {report['total']}")
print()
for cat, names in sorted(report['by_category'].items()):
    print(f"[{cat}] ({len(names)})")
    for n in sorted(names):
        print(f"  - {n}")
    print()
