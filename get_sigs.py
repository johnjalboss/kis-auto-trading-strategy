import inspect
import importlib

# Fix the known bug in vix_structure.py dynamically so import works without failing if get_vix_metrics runs at import (it shouldn't, but just in case)
modules = ["performance_diagnosis", "winrate_optimizer", "performance_attribution", "auto_compound", "auto_tuner", "trade_journal", "ml_predictor", "fed_watch", "intermarket", "correlation_regime", "sector_rotator", "economic_calendar", "stress_test", "liquidity_filter", "vix_structure"]

if __name__ == "__main__":
    with open("signatures.txt", "w", encoding="utf-8") as f:
        for mod_name in modules:
            try:
                mod = importlib.import_module(mod_name)
                f.write(f"\n--- {mod_name} ---\n")
                for item in dir(mod):
                    if item.startswith('_'): continue
                    obj = getattr(mod, item)
                    if inspect.isclass(obj) and getattr(obj, '__module__', '') == mod_name:
                        f.write(f"class {item}:\n")
                        for name, func in inspect.getmembers(obj, predicate=lambda x: inspect.isfunction(x) or inspect.ismethod(x)):
                            if not name.startswith('_') or name == "__init__":
                                try:
                                    sig = inspect.signature(func)
                                    f.write(f"  def {name}{sig}\n")
                                except:
                                    f.write(f"  def {name}(...)\n")
                    elif inspect.isfunction(obj) and getattr(obj, '__module__', '') == mod_name:
                        try:
                            sig = inspect.signature(obj)
                            f.write(f"def {item}{sig}\n")
                        except:
                            f.write(f"def {item}(...)\n")
            except Exception as e:
                f.write(f"Failed {mod_name}: {e}\n")
