"""Check all non-discovered modules for their class methods"""
import importlib, inspect, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

targets = ['exit_optimizer','drawdown_controller','drawdown_recovery','dynamic_stop',
           'manipulation_defense','alpha_generator','macro_shield','monte_carlo',
           'ml_predictor','ai_judge','high_performance','winrate_optimizer',
           'portfolio','trailing_stop','gap_scanner','premarket',
           'dynamic_scaling','hedge_manager','stress_test','performance_attribution',
           'performance_diagnosis','anti_fragility','cost_model','economic_calendar',
           'emergency_stop','execution_tracker','frequency_controller','notification',
           'realtime_monitor','trade_journal','reporter','kelly_criterion',
           'position_sizer','tax_optimizer','smart_order']

for mod_name in sorted(targets):
    try:
        mod = importlib.import_module(mod_name)
        classes = [(n, [m for m in dir(obj) if not m.startswith('_') and callable(getattr(obj,m,None))])
                   for n, obj in inspect.getmembers(mod, inspect.isclass)
                   if obj.__module__ == mod_name]
        funcs = [n for n, obj in inspect.getmembers(mod, inspect.isfunction)
                 if obj.__module__ == mod_name]
        if classes:
            for cname, methods in classes:
                print(f"  {mod_name}.{cname}: {methods[:10]}")
        elif funcs:
            print(f"  {mod_name} (functions only): {funcs[:10]}")
        else:
            print(f"  {mod_name}: empty")
    except Exception as e:
        print(f"  {mod_name}: FAIL: {str(e)[:80]}")
