import os
import importlib
import inspect
import sys
sys.path.insert(0, '.')

blacklist = [
    'main', 'test_', 'backtest', 'deploy', 'orchestrator', 
    'kis_', 'read_', 'extract_', 'verify', 'dashboard', 
    'Start_', '__', 'check_', 'diag_', 'integration_test',
    'base_adapters', 'base_analyzer', 'config', 'audit_',
    'ai_judge', 'all_modules_', 'competition_mode', 'reporter',
    'trader', 'strategy', 'screener', 'risk_manager', 'database',
    'data_proxy', 'auth', 'keepalive', 'health_monitor', 'watchdog',
    'scheduler', 'notification', 'notifier', 'smart_order', 'indicators',
    'utils', 'trade', 'composite_signal', 'signal_aggregator',
    'frequency_controller', 'server_', 'fix_', 'debug_', 'temp_'
]

ANALYSIS_METHODS = {
    'analyze', 'detect', 'check', 'evaluate', 'predict', 'scan',
    'full_scan', 'calculate', 'generate', 'get_score', 'get_opportunity_score',
    'calculate_macro_score', 'filter_macro_headwinds', 'check_today',
    'is_trade_worth_it', 'scan_watchlist', 'is_safe_to_trade',
    'quick_check', 'calculate_position_size', 'get_stats', 'get_recent',
    'calculate_entry_cost', 'get_hedge_positions', 'get_drawdown'
}

if __name__ == "__main__":
    for f in sorted(os.listdir('.')):
        if f.endswith('.py') and not any(b in f for b in blacklist):
            mod_name = f[:-3]
            try:
                mod = importlib.import_module(mod_name)
                for name, cls in inspect.getmembers(mod, inspect.isclass):
                    if cls.__module__ == mod_name:
                        for m_name in ANALYSIS_METHODS:
                            if hasattr(cls, m_name):
                                method = getattr(cls, m_name)
                                if callable(method):
                                    sig = inspect.signature(method)
                                    params = list(sig.parameters.keys())
                                    print(f"{mod_name}.{name}.{m_name}() -> params: {params}")
            except Exception as e:
                print(f"Failed to load {mod_name}: {e}")
