import inspect
import candlestick

methods = set([
    'analyze', 'detect', 'check', 'evaluate', 'predict', 'scan',
    'should_exit', 'should_trade', 'should_harvest', 'should_reduce_exposure',
    'should_rotate_to_safe', 'full_scan', 'run_test', 'diagnose',
    'simulate', 'optimize', 'calculate', 'generate', 'rank_symbols',
    'is_safe_to_trade', 'quick_check', 'get_score', 'get_opportunity_score',
    'calculate_macro_score', 'filter_macro_headwinds', 'check_today',
    'is_trade_worth_it', 'scan_watchlist', 'get_stops', 'update',
    'get_phase', 'get_allocation', 'get_targets',
    'check_flash_crash', 'check_portfolio_loss', 'check_vix_spike',
    'calculate_position_size', 'get_growth_plan', 'update_capital',
    'force_stop', 'get_drawdown', 'get_stats', 'record', 'get_optimal_time',
    'get_best_performers', 'get_strategy_stats', 'record_trade',
    'analyze_by_regime', 'analyze_by_strategy', 'get_improvement_priority',
    'generate_daily_report', 'get_top_performers', 'check_now',
    'log_trade', 'get_recent', 'calculate_entry_cost',
    'get_crisis_actions', 'get_hedge_positions'
])

for name, cls in inspect.getmembers(candlestick, inspect.isclass):
    if cls.__module__ == 'candlestick':
        found = []
        for m in methods:
            if hasattr(cls, m) and callable(getattr(cls, m)):
                found.append(m)
        print(f"{name}: {found}")
