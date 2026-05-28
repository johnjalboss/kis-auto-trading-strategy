"""Simple Import + Basic Function Audit — saves results to audit_output.txt"""
import sys, importlib, time, json
from loguru import logger

def run_audit():
    logger.remove()
    OUT = open("audit_output.txt", "w")
    def log(msg):
        print(msg)
        OUT.write(msg + "\n")
        OUT.flush()

    MODULES = [
        'config', 'trader', 'database', 'risk_manager', 'strategy', 'notification',
        'keepalive', 'kis_data', 'data_proxy', 'macro', 'regime_detector',
        'fed_watch', 'macro_shield', 'geopolitical', 'intermarket',
        'correlation_matrix', 'correlation_regime', 'sector_rotation',
        'economic_calendar', 'event_calendar', 'market_breadth', 'market_internals',
        'stress_test', 'alpha_generator', 'candlestick', 'divergence', 'fibonacci',
        'gap_scanner', 'intraday_momentum', 'momentum_ranking', 'order_flow',
        'squeeze_detector', 'accumulation', 'premarket', 'premarket_gap',
        'realtime_monitor', 'volume_profile', 'statistical_arbitrage', 'mean_reversion',
        'smart_money', 'sentiment', 'social_sentiment',
        'news_analyzer', 'insider_tracker', 'etf_flows', 'options_flow',
        'crypto_sentiment', 'earnings_analyzer', 'earnings_calendar', 'credit_spreads',
        'liquidity_analyzer', 'drawdown_controller', 'drawdown_recovery',
        'dynamic_stop', 'dynamic_scaling', 'emergency_stop', 'exit_optimizer',
        'frequency_controller', 'position_sizer', 'portfolio', 'cost_model',
        'anti_fragility', 'liquidity_filter', 'manipulation_defense', 'monte_carlo',
        'factor_analysis', 'smart_order', 'trade_journal', 'composite_signal',
        'base_adapters', 'auto_tuner', 'auto_compound', 'adaptive_strategy',
        'competition_mode', 'ai_judge', 'execution_tracker', 'health_checker',
        'screener', 'orchestrator', 'auth',
    ]

    log("=" * 60)
    log("PHASE 1: IMPORT TEST")
    log("=" * 60)
    passed = 0
    failed = 0
    fail_list = []
    for m in MODULES:
        try:
            importlib.import_module(m)
            passed += 1
            log(f"  OK  {m}")
        except Exception as e:
            failed += 1
            err = f"{type(e).__name__}: {str(e)[:120]}"
            fail_list.append((m, err))
            log(f"  FAIL {m} — {err}")

    log(f"\nImport: {passed} OK / {failed} FAIL out of {len(MODULES)}")

    # PHASE 2: Functional tests with real data
    log("\n" + "=" * 60)
    log("PHASE 2: FUNCTIONAL TESTS")
    log("=" * 60)

    import yfinance as yf
    import pandas as pd
    import numpy as np

    df = yf.download("AAPL", period="90d", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    log(f"Test data: AAPL {len(df)} rows")

    func_pass = 0
    func_fail = 0
    func_fails = []

    # Test macro
    try:
        from macro import get_macro_score
        r = get_macro_score()
        log(f"  OK  macro.get_macro_score() -> {r}")
        func_pass += 1
    except Exception as e:
        log(f"  FAIL macro: {e}")
        func_fail += 1
        func_fails.append(("macro", str(e)[:120]))

    # Test screener (skip full screen, just test import and init)
    try:
        from screener import DynamicScreener
        s = DynamicScreener()
        log(f"  OK  screener.DynamicScreener() initialized")
        func_pass += 1
    except Exception as e:
        log(f"  FAIL screener init: {e}")
        func_fail += 1
        func_fails.append(("screener", str(e)[:120]))

    # Test composite_signal
    try:
        from composite_signal import CompositeSignalEngine
        engine = CompositeSignalEngine()
        result = engine.analyze("AAPL")
        log(f"  OK  composite_signal.analyze('AAPL') -> {result.action.value} Score:{result.composite_score} Conf:{result.confidence}%")
        func_pass += 1
    except Exception as e:
        log(f"  FAIL composite_signal: {e}")
        func_fail += 1
        func_fails.append(("composite_signal", str(e)[:120]))

    # Test base_adapters discovery
    try:
        from base_adapters import get_available_adapters
        adapters = get_available_adapters()
        n = len(adapters) if adapters else 0
        log(f"  OK  base_adapters: {n} adapters discovered")
        func_pass += 1
        # List categories
        cats = {}
        for a in adapters:
            try:
                inst = a()
                c = inst.category
                cats[c] = cats.get(c, 0) + 1
            except:
                pass
        for c, count in sorted(cats.items()):
            log(f"       {c}: {count} adapters")
    except Exception as e:
        log(f"  FAIL base_adapters: {e}")
        func_fail += 1
        func_fails.append(("base_adapters", str(e)[:120]))

    # Test technical modules with real data
    TECH_TO_TEST = [
        ("alpha_generator", "AlphaGenerator", "generate"),
        ("candlestick", "CandlestickAnalyzer", "analyze"),
        ("divergence", "DivergenceDetector", "detect"),
        ("squeeze_detector", "SqueezeDetector", "detect"),
        ("momentum_ranking", "MomentumRanker", "rank"),
        ("gap_scanner", "GapScanner", "scan"),
        ("fibonacci", "FibonacciAnalyzer", "analyze"),
        ("volume_profile", "VolumeProfileAnalyzer", "analyze"),
        ("trend_strength", "TrendStrengthAnalyzer", "analyze"),
        ("smart_money", "SmartMoneyTracker", "analyze"),
        ("sentiment", "SentimentAnalyzer", "analyze"),
    ]

    for mod_name, cls_name, method_name in TECH_TO_TEST:
        try:
            mod = importlib.import_module(mod_name)
            cls = getattr(mod, cls_name, None)
            if cls is None:
                # Try to find any class
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if isinstance(attr, type) and attr_name[0].isupper() and not attr_name.startswith('_'):
                        cls = attr
                        cls_name = attr_name
                        break
            if cls is None:
                log(f"  WARN {mod_name}: no class found")
                continue
            instance = cls()
            func = None
            for mn in [method_name, 'analyze', 'detect', 'scan', 'check', 'evaluate']:
                if hasattr(instance, mn):
                    func = getattr(instance, mn)
                    method_name = mn
                    break
            if func is None:
                log(f"  WARN {mod_name}.{cls_name}: no callable method")
                continue
            try:
                result = func(df, symbol="AAPL")
            except TypeError:
                try:
                    result = func(df)
                except TypeError:
                    result = func("AAPL")
            log(f"  OK  {mod_name}.{cls_name}.{method_name}() -> {type(result).__name__}")
            func_pass += 1
        except Exception as e:
            log(f"  FAIL {mod_name}: {type(e).__name__}: {str(e)[:100]}")
            func_fail += 1
            func_fails.append((mod_name, str(e)[:120]))

    # Test trader.get_price
    try:
        from trader import Trader
        t = Trader()
        t._token_mgr.get_token()
        price = t.get_price("AAPL")
        log(f"  OK  trader.get_price('AAPL') -> ${price:.2f}")
        func_pass += 1
        # test a troublesome symbol
        price2 = t.get_price("BROS")
        log(f"  OK  trader.get_price('BROS') -> ${price2:.2f} (prev error symbol)")
        func_pass += 1
    except Exception as e:
        log(f"  FAIL trader.get_price: {e}")
        func_fail += 1
        func_fails.append(("trader.get_price", str(e)[:120]))

    log(f"\nFunctional: {func_pass} OK / {func_fail} FAIL")

    # Final Summary
    log("\n" + "=" * 60)
    log("FINAL SUMMARY")
    log("=" * 60)
    total_p = passed + func_pass
    total_f = failed + func_fail
    log(f"Total: {total_p} PASS / {total_f} FAIL")

    if fail_list:
        log("\nIMPORT FAILURES:")
        for m, err in fail_list:
            log(f"  X {m}: {err}")

    if func_fails:
        log("\nFUNCTIONAL FAILURES:")
        for m, err in func_fails:
            log(f"  X {m}: {err}")

    OUT.close()

if __name__ == "__main__":
    run_audit()
