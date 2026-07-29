import sys
import os
import strategy
from loguru import logger

print("-" * 40)
print(f"Python Path: {sys.path}")
print(f"Strategy File: {getattr(strategy, '__file__', 'N/A')}")
print(f"Strategy Members: {[m for m in dir(strategy) if not m.startswith('__')]}")
print("-" * 40)

try:
    from strategy import get_strategy
    print("SUCCESS: get_strategy imported successfully")
except ImportError as e:
    print(f"ERROR: Cannot import get_strategy: {e}")
except Exception as e:
    print(f"ERROR: Unexpected error during import: {e}")
