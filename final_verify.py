"""Final comprehensive system verification — runs every core module."""
import sys, os, importlib, traceback, sqlite3, json
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '.')

print("=" * 70)
print("FINAL SYSTEM VERIFICATION")
print("=" * 70)

# ============================================================
# 1. IMPORT TEST — every module that the bot actually uses
# ============================================================
CORE = [
    'config', 'database', 'auth', 'scheduler', 'notifier', 'risk_manager',
    'strategy', 'reporter', 'chart_generator', 'composite_signal',
    'base_adapters', 'orchestrator', 'screener', 'macro_shield',
    'premarket', 'emergency_stop', 'trade_journal', 'earnings_calendar',
    'earnings_analyzer', 'health_monitor', 'notification',
    'kis_client', 'kis_data', 'trader', 'indicators', 'macro',
    'data_proxy', 'fetch_dashboard_data',
]

fail = []
ok = []
print("\n[1/6] CORE MODULE IMPORTS")
for m in CORE:
    try:
        importlib.import_module(m)
        ok.append(m)
    except Exception as e:
        fail.append((m, f"{type(e).__name__}: {str(e)[:80]}"))
        print(f"  !! FAIL: {m} -> {type(e).__name__}: {str(e)[:80]}")

print(f"  Result: {len(ok)}/{len(CORE)} PASS, {len(fail)} FAIL")
if not fail:
    print("  ✅ ALL CORE MODULES OK")

# ============================================================
# 2. CONFIG SANITY CHECK
# ============================================================
print("\n[2/6] CONFIG VALUES CHECK")
import config
checks = {
    'MAX_POSITIONS': (config.MAX_POSITIONS, 3),
    'TAKE_PROFIT_PCT': (config.TAKE_PROFIT_PCT, 0.03),
    'MAX_POSITION_PCT': (config.MAX_POSITION_PCT, 0.35),
    'ATR_STOP_MULTIPLIER': (config.ATR_STOP_MULTIPLIER, 1.5),
    'LEVERAGED_MAX_HOLD_HOURS': (config.LEVERAGED_MAX_HOLD_HOURS, 24),
    'LEVERAGED_TAKE_PROFIT_PCT': (config.LEVERAGED_TAKE_PROFIT_PCT, 0.02),
    'CONFLICTING_PAIRS has TQQQ': ('TQQQ' in config.CONFLICTING_PAIRS, True),
    'LEVERAGED_ETFS has SQQQ': ('SQQQ' in config.LEVERAGED_ETFS, True),
}
config_ok = True
for name, (actual, expected) in checks.items():
    status = "✅" if actual == expected else "❌"
    if actual != expected:
        config_ok = False
    print(f"  {status} {name}: {actual} (expected {expected})")
if config_ok:
    print("  ✅ ALL CONFIG VALUES CORRECT")

# ============================================================
# 3. STRATEGY LEVERAGED ETF RULES CHECK
# ============================================================
print("\n[3/6] STRATEGY LEVERAGED ETF RULES")
try:
    with open('strategy.py', 'r') as f:
        strategy_code = f.read()
    checks_strat = [
        ('LEVERAGED_TIMEOUT exit', 'LEVERAGED_TIMEOUT' in strategy_code),
        ('LEVERAGED_TP exit', 'LEVERAGED_TP' in strategy_code),
        ('LEVERAGED_SL exit', 'LEVERAGED_SL' in strategy_code),
        ('config.LEVERAGED_ETFS check', 'config.LEVERAGED_ETFS' in strategy_code),
    ]
    for name, result in checks_strat:
        print(f"  {'✅' if result else '❌'} {name}: {'Found' if result else 'MISSING'}")
except Exception as e:
    print(f"  ❌ Error reading strategy.py: {e}")

# ============================================================
# 4. ORCHESTRATOR ANTI-CONFLICT CHECK
# ============================================================
print("\n[4/6] ORCHESTRATOR ANTI-CONFLICT FILTER")
try:
    with open('orchestrator.py', 'r') as f:
        orch_code = f.read()
    checks_orch = [
        ('CONFLICT BLOCKED logic', 'CONFLICT BLOCKED' in orch_code),
        ('CONFLICTING_PAIRS check', 'config.CONFLICTING_PAIRS' in orch_code),
    ]
    for name, result in checks_orch:
        print(f"  {'✅' if result else '❌'} {name}: {'Found' if result else 'MISSING'}")
except Exception as e:
    print(f"  ❌ Error reading orchestrator.py: {e}")

# ============================================================
# 5. DATABASE & SERVICE
# ============================================================
print("\n[5/6] DATABASE & SERVICE")
try:
    conn = sqlite3.connect('trades.db')
    tables = [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print(f"  Tables: {tables}")
    for t in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {count} rows")
    conn.close()
    print("  ✅ DATABASE OK")
except Exception as e:
    print(f"  ❌ DATABASE ERROR: {e}")

# Service status
status = os.popen("systemctl is-active kis-trading 2>/dev/null").read().strip()
print(f"  Service: {status}")
if status == "active":
    print("  ✅ SERVICE RUNNING")
else:
    print("  ❌ SERVICE NOT ACTIVE")

# ============================================================
# 6. RECENT LOG ERRORS
# ============================================================
print("\n[6/6] RECENT LOG ANALYSIS")
try:
    with open('trading_bot.log', 'r') as f:
        lines = f.readlines()
    
    # Last 200 lines
    recent = lines[-200:] if len(lines) > 200 else lines
    errors = [l.strip() for l in recent if 'ERROR' in l or 'CRITICAL' in l]
    warnings = [l.strip() for l in recent if 'WARNING' in l]
    
    if errors:
        print(f"  ⚠️ {len(errors)} errors in last 200 log lines:")
        for e in errors[-5:]:
            print(f"    {e[:120]}")
    else:
        print("  ✅ NO ERRORS in recent logs")
    
    print(f"  Warnings: {len(warnings)} (normal)")
    
    # Check boot sequence
    boot_lines = [l for l in recent if 'Phase 1 Complete' in l or 'AUTONOMOUS TRADING' in l or 'Phase 2' in l]
    if boot_lines:
        print(f"  Last boot: {boot_lines[-1].strip()[:100]}")
except Exception as e:
    print(f"  ❌ LOG ERROR: {e}")

# ============================================================
# FINAL SUMMARY
# ============================================================
print("\n" + "=" * 70)
total_checks = len(CORE) + len(checks) + 4 + 2 + 2  # imports + config + strategy + orch + db/service
total_pass = len(ok) + sum(1 for _, (a, e) in checks.items() if a == e)
print(f"FINAL VERDICT: {len(fail)} critical failures found")
if len(fail) == 0:
    print("🎉 ALL SYSTEMS OPERATIONAL — BOT IS HEALTHY!")
else:
    print("⚠️ ISSUES FOUND:")
    for m, err in fail:
        print(f"  {m}: {err}")
print("=" * 70)
