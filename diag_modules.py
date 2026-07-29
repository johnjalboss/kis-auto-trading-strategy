"""Auto-discovery diagnostic: find which modules fail and why"""
import os, sys, importlib, inspect
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')

from dotenv import load_dotenv
load_dotenv()

BLACKLIST = ['main', 'test_', 'backtest', 'deploy', 'orchestrator', 'kis_', 'read_', 
             'extract_', 'verify_', 'dashboard', 'Start_', '__']

current_dir = os.path.dirname(os.path.abspath(__file__))
loaded = []
failed = []
no_class = []

for f in sorted(os.listdir(current_dir)):
    if not f.endswith('.py') or f == 'base_adapters.py':
        continue
    if any(b in f for b in BLACKLIST):
        continue
    
    mod_name = f[:-3]
    try:
        mod = importlib.import_module(mod_name)
        # Check if it has analyzable classes
        classes = [name for name, obj in inspect.getmembers(mod, inspect.isclass)
                   if obj.__module__ == mod_name and 
                   (hasattr(obj, 'analyze') or hasattr(obj, 'detect') or hasattr(obj, 'check'))]
        if classes:
            loaded.append((mod_name, classes))
        else:
            no_class.append(mod_name)
    except Exception as e:
        failed.append((mod_name, str(e)[:120]))

print(f"=== LOADED ({len(loaded)}) ===")
for name, classes in loaded:
    print(f"  OK {name}: {classes}")

print(f"\n=== NO ANALYZABLE CLASS ({len(no_class)}) ===")
for name in no_class:
    print(f"  -- {name}")

print(f"\n=== FAILED ({len(failed)}) ===")
for name, err in failed:
    print(f"  XX {name}: {err}")

print(f"\nTotal: {len(loaded)} loaded, {len(no_class)} no class, {len(failed)} failed")
