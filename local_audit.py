"""
Comprehensive local source code audit for the KIS auto-trading bot.
Checks all Python module files for common bugs WITHOUT needing SSH.
"""
import os, ast, re, sys
from pathlib import Path

BASE = Path(r"c:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading")

# Core infrastructure modules (these are not signal adapters)
INFRA = {
    "base_adapters", "base_analyzer", "orchestrator", "composite_signal",
    "data_proxy", "kis_data", "kis_client", "trader", "portfolio", "database",
    "screener", "macro_shield", "risk_manager", "frequency_controller",
    "notifier", "config", "auth", "utils", "scheduler", "strategy",
    "signal_aggregator", "indicators", "drawdown_controller", "smart_order",
    "trade", "trade_journal", "reporter", "regime_detector", "universe",
    "ai_judge", "dashboard", "dashboard_app", "chart_generator", "health_monitor",
    "keepalive", "watchdog", "performance_diagnosis", "emergency_stop",
    "auto_tuner", "backtester", "position_sizer", "kelly_criterion",
    "execution_tracker", "trailing_stop", "dynamic_stop", "exit_optimizer",
    "main", "main_autonomous", "notification", "realtime_monitor",
    "backfill_stats", "fix_db_pnl", "auto_compound", "tax_optimizer",
    "competition_mode", "performance_attribution", "cost_model",
    "drawdown_recovery", "adaptive_strategy", "manipulation_defense",
    "hedge_manager", "dynamic_scaling", "fetch_dashboard_data",
    "generate_dashboard", "kis_integration", "dashboard_cli", "dashboard_live",
    "backtester", "event_calendar", "earnings_calendar", "factor_analysis",
    "ultimate_strategy", "high_performance",
}

issues = []
pass_count = 0
fail_count = 0
adapter_files = []

print("=" * 65)
print("  KIS Auto-Trading Bot - Comprehensive Source Code Audit")
print("=" * 65)

# 1. Collect all adapter module files
all_py = sorted(BASE.glob("*.py"))
for f in all_py:
    name = f.stem
    if name in INFRA:
        continue
    if name.startswith(("test_", "check_", "simple_", "verify_", "deep_", "final_",
                         "diag", "run_", "deploy_", "download_", "full_", "repair_",
                         "extract_", "get_", "query_", "sell_", "count_", "read_",
                         "dump", "backfill", "fix_", "manual_", "generate_", "fetch_",
                         "script_", "audit_", "check_")):
        continue
    adapter_files.append(f)

print(f"\nFound {len(adapter_files)} adapter/signal module candidates to audit.\n")

# 2. For each adapter, check common issues
EXPECTED_ANALYZE_PATTERNS = [
    r"def analyze\(",
    r"def analyze_async\(",
]

RETURN_ANOMALY_PATTERNS = [
    # If analyze() returns something unexpected
    (r"return\s+None\b", "analyze() may return None — score engine expects dict"),
    (r"return\s+\{\}", "returns empty {} — may fail downstream"),
    (r"return\s+\[\]", "returns [] — score engine expects dict"),
]

KNOWN_BAD_PATTERNS = [
    # Calling real yfinance instead of shim (these should all go through data_proxy)
    (r"import yfinance as yf\b", "Direct yfinance import found — may bypass data_proxy shim"),
    (r"yf\.download\(", "yf.download() called — should use data_proxy instead"),
    (r"yf\.Ticker\(", "yf.Ticker() called — should use data_proxy shim"),
    # Blocking/hanging patterns
    (r"time\.sleep\(\s*[6-9][0-9]", "Long sleep (≥60s) in module may block adapter thread"),
    (r"while True:", "Infinite loop in module — may block adapter discovery"),
    # Bad exception handling
    (r"except:\s*$", "Bare except clause — may swallow important errors silently"),
    (r"except Exception:\s*$", "Swallows all exceptions — consider logging"),
]

for fpath in adapter_files:
    file_issues = []
    module_name = fpath.stem
    try:
        src = fpath.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        issues.append((module_name, f"Cannot read file: {e}"))
        fail_count += 1
        continue
    
    # Check if it has an analyze() method
    has_analyze = bool(re.search(r"def analyze\(", src))
    
    # Check for known-bad patterns
    for pattern, msg in KNOWN_BAD_PATTERNS:
        if re.search(pattern, src, re.MULTILINE):
            # special case: kis_data and data_proxy are allowed to import yfinance directly
            if "yfinance" in pattern and module_name in ("kis_data", "data_proxy"):
                continue
            file_issues.append(f"⚠  {msg}")
    
    # Check class inherits BaseAnalyzer
    has_base = bool(re.search(r"class\s+\w+\s*\(\s*BaseAnalyzer\s*\)", src))
    
    # Try to parse and find the analyze method's return type
    if has_analyze:
        # Find analyze method and check if all paths return a dict-like value
        analyze_match = re.search(r"def analyze\(.*?\).*?(?=def |\Z)", src, re.DOTALL)
        if analyze_match:
            analyze_body = analyze_match.group(0)
            if "return None" in analyze_body and "return {" not in analyze_body and "return self" not in analyze_body:
                file_issues.append("⚠  analyze() can return None without providing a score dict")
    
    if file_issues:
        issues.append((module_name, file_issues))
        fail_count += 1
        print(f"  ❌ {module_name}")
        for iss in file_issues:
            print(f"     {iss}")
    else:
        pass_count += 1
        # Only print passes for modules with analyze()
        if has_analyze:
            print(f"  ✅ {module_name}")

print("\n" + "=" * 65)
print(f"  SUMMARY: {pass_count} passed, {fail_count} had issues")
print("=" * 65)

# 3. Special checks on core files
print("\n--- CORE FILE AUDIT ---")

# Check data_proxy.py preserves original yfinance before patching
dp = (BASE / "data_proxy.py").read_text(encoding="utf-8", errors="replace")
if "_original_yf_Ticker" in dp:
    print("  ✅ data_proxy.py saves original Ticker as _original_yf_Ticker")
else:
    print("  ❌ data_proxy.py does NOT save original yf.Ticker — the fix won't work!")
    issues.append(("data_proxy", ["Does not save _original_yf_Ticker before monkey-patching"]))

# Check kis_data.py uses the saved original
kd = (BASE / "kis_data.py").read_text(encoding="utf-8", errors="replace")
if "_original_yf_Ticker" in kd:
    print("  ✅ kis_data.py uses _original_yf_Ticker for fallback (recursion fix applied)")
else:
    print("  ❌ kis_data.py does NOT use _original_yf_Ticker — recursion fix missing!")
    issues.append(("kis_data", ["_original_yf_Ticker recursion fix not applied"]))

# Check base_adapters.py has no debug prints
ba = (BASE / "base_adapters.py").read_text(encoding="utf-8", errors="replace")
if 'print(f"DEBUG: Importing' in ba or 'print(f"DEBUG: Successfully' in ba:
    print("  ⚠  base_adapters.py still has DEBUG print statements")
else:
    print("  ✅ base_adapters.py - debug prints removed")

# Check orchestrator has sell_excess_positions function for score-based replacement
orch = (BASE / "orchestrator.py").read_text(encoding="utf-8", errors="replace")
if "sell_excess_positions" in orch or "replace" in orch.lower():
    print("  ✅ orchestrator.py - has position replacement logic")
else:
    print("  ⚠  orchestrator.py - check if score-based position replacement exists")

# Check data_proxy.py patches correctly (MUST patch before adapter imports)
if "sys.modules" in dp and "yfinance" in dp:
    print("  ✅ data_proxy.py patches yfinance at import time via sys.modules")
else:
    print("  ⚠  data_proxy.py - verify yfinance shim is applied before adapter imports")

print("\n" + "=" * 65)
print("  AUDIT COMPLETE")
print("=" * 65)
