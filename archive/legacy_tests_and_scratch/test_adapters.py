import sys, os, traceback
sys.path.append('/home/ubuntu/kis-auto-trading')
import kis_data
from base_adapters import get_available_adapters

df = kis_data.download('NVDA', period='90d')
if hasattr(df, 'columns') and hasattr(df.columns, 'get_level_values'):
    import pandas as pd
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

print(f"df shape: {df.shape}")
print("Testing all adapters with NVDA data...")

adapters = get_available_adapters()
for Cls in adapters:
    try:
        inst = Cls()
        result = inst.analyze(df, symbol='NVDA')
        print(f"OK: {inst.name}")
    except Exception as e:
        print(f"FAIL: {Cls.__name__}: {e}")
