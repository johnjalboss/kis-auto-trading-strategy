import importlib

modules = ["performance_diagnosis", "winrate_optimizer", "performance_attribution", 
           "auto_compound", "auto_tuner", "trade_journal", "ml_predictor", 
           "fed_watch", "vix_structure", "intermarket", "correlation_regime", 
           "sector_rotator", "economic_calendar", "stress_test", "liquidity_filter"]

for mod_name in modules:
    try:
        mod = importlib.import_module(mod_name)
        print(f"\n--- {mod_name} ---")
        for item in dir(mod):
            if not item.startswith('_') and item not in ['datetime', 'time', 'pd', 'np', 'os', 'sys', 'json', 're', 'math', 'loguru', 'logger', 'Any', 'Dict', 'List', 'Optional', 'Tuple', 'Union']:
                obj = getattr(mod, item)
                if callable(obj) or isinstance(obj, type):
                    print(f"  {item}")
    except Exception as e:
        print(f"\nFailed {mod_name}: {e}")
