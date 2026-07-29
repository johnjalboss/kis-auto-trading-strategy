#!/usr/bin/env python3
"""
DEFINITIVE Full Module Audit
Checks:
1. ALL BaseAnalyzer subclasses (what composite_signal actually loads)
2. ALL orchestrator-imported modules
3. ALL market-wide analyzers
4. ALL utility modules
Reports per-module status with import test + function call test.
"""
import sys, os, importlib, traceback, json, inspect
from pathlib import Path

BASE = Path("/home/ubuntu/kis-auto-trading")
sys.path.insert(0, str(BASE))
os.chdir(str(BASE))

from dotenv import load_dotenv
load_dotenv()

import data_proxy  # patches yfinance -> KIS

from loguru import logger
logger.remove()

results = []
seen = set()

def record(name, category, status, note=""):
    if name not in seen:
        seen.add(name)
        results.append({"name": name, "category": category, "status": status, "note": note})
        emoji = "PASS" if status == "PASS" else ("SKIP" if status == "SKIP" else "FAIL")
        print(f"  [{emoji}] {name} ({category}): {note[:80]}")

print("=" * 65)
print("DEFINITIVE FULL MODULE AUDIT")
print("=" * 65)

# ── SECTION 1: BaseAnalyzer subclasses (composite_signal adapters) ──
print("\n[1] Testing all BaseAnalyzer subclasses (composite_signal adapters)...")
try:
    from base_analyzer import BaseAnalyzer
    import pkgutil
    
    all_py = sorted(BASE.glob("*.py"))
    for fpath in all_py:
        name = fpath.stem
        if name in ("base_analyzer", "base_adapters", "data_proxy", "config"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(name, fpath)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            
            for attr_name in dir(mod):
                cls = getattr(mod, attr_name, None)
                if (cls and isinstance(cls, type) and 
                    issubclass(cls, BaseAnalyzer) and cls is not BaseAnalyzer):
                    try:
                        instance = cls()
                        # Test analyze with a DataFrame
                        import pandas as pd, numpy as np
                        dates = pd.date_range("2025-01-01", periods=60, freq="B")
                        df = pd.DataFrame({
                            "Open": np.random.uniform(100,200,60),
                            "High": np.random.uniform(100,200,60),
                            "Low": np.random.uniform(100,200,60),
                            "Close": np.random.uniform(100,200,60),
                            "Volume": np.random.randint(1000000,5000000,60),
                        }, index=dates)
                        result = instance.analyze(df, symbol="AAPL")
                        score = result.get("score","N/A") if isinstance(result,dict) else "ok"
                        record(name, "BaseAnalyzer", "PASS", f"class={attr_name} score={score}")
                    except Exception as e:
                        record(name, "BaseAnalyzer", "FAIL", f"class={attr_name}: {str(e)[:60]}")
                    break
        except Exception:
            pass
except Exception as e:
    print(f"  BaseAnalyzer import error: {e}")

# ── SECTION 2: Market-wide analyzers (called by orchestrator directly) ──
print("\n[2] Testing market-wide analyzers (no-symbol analyze())...")
MARKET_WIDE = [
    "fed_watch", "vix_structure", "global_macro", "market_breadth",
    "market_internals", "market_psychology", "geopolitical", "yen_carry",
    "intermarket", "macro", "crypto_sentiment", "etf_flows", "oil_impact",
    "sector_rotation", "sector_rotator", "credit_spreads", "hidden_markov_regime",
]
for mod_name in MARKET_WIDE:
    if mod_name in seen:
        continue
    try:
        if mod_name in sys.modules:
            del sys.modules[mod_name]
        mod = importlib.import_module(mod_name)
        # Find class with analyze(self) - no symbol
        found = False
        for attr_name in dir(mod):
            cls = getattr(mod, attr_name, None)
            if cls and isinstance(cls, type) and hasattr(cls, 'analyze'):
                try:
                    sig = inspect.signature(cls.analyze)
                    params = list(sig.parameters.keys())
                    if params == ['self']:
                        instance = cls()
                        result = instance.analyze()
                        score = getattr(result, 'score', getattr(result, 'fed_score', 'ok'))
                        record(mod_name, "MarketWide", "PASS", f"analyze() -> score={score}")
                        found = True
                        break
                except Exception as e:
                    record(mod_name, "MarketWide", "FAIL", str(e)[:70])
                    found = True
                    break
        if not found:
            record(mod_name, "MarketWide", "SKIP", "no no-arg analyze() found")
    except Exception as e:
        record(mod_name, "MarketWide", "FAIL", f"import error: {str(e)[:60]}")

# ── SECTION 3: Utility modules (called by trader/risk_manager etc.) ──
print("\n[3] Testing utility modules (import check only)...")
UTILITY_MODULES = [
    "trailing_stop", "dynamic_stop", "kelly_criterion", "monte_carlo",
    "stress_test", "performance_attribution", "winrate_optimizer",
    "alpha_generator", "anti_fragility", "ml_predictor", "gap_scanner",
    "liquidity_filter", "manipulation_defense", "premarket", "economic_calendar",
    "hedge_manager", "drawdown_controller", "drawdown_recovery",
    "position_sizer", "smart_order", "exit_optimizer", "execution_tracker",
    "auto_tuner", "regime_detector", "macro_shield", "risk_manager",
    "signal_aggregator",
]
for mod_name in UTILITY_MODULES:
    if mod_name in seen:
        continue
    try:
        if mod_name in sys.modules:
            del sys.modules[mod_name]
        mod = importlib.import_module(mod_name)
        # Just verify import succeeds + has main classes/functions
        attrs = [a for a in dir(mod) if not a.startswith('_')]
        record(mod_name, "Utility", "PASS", f"import ok, {len(attrs)} public attrs")
    except Exception as e:
        record(mod_name, "Utility", "FAIL", f"import error: {str(e)[:60]}")

# ── SUMMARY ──
passes = [r for r in results if r["status"] == "PASS"]
fails = [r for r in results if r["status"] == "FAIL"]
skips = [r for r in results if r["status"] == "SKIP"]

print("\n" + "=" * 65)
print(f"DEFINITIVE AUDIT COMPLETE — {len(results)} total modules checked")
print(f"  PASS: {len(passes)}")
print(f"  FAIL: {len(fails)}")
print(f"  SKIP: {len(skips)}")
print("=" * 65)

if fails:
    print("\nFAILED MODULES:")
    for r in fails:
        print(f"  - {r['name']} ({r['category']}): {r['note']}")

with open("/tmp/definitive_audit.json", "w") as f:
    json.dump({"passes": passes, "fails": fails, "skips": skips, "total": len(results)}, f, indent=2)
print(f"\nSaved to /tmp/definitive_audit.json")
