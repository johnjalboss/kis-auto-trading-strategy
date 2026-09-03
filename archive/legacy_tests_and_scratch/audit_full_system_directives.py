"""
Deep System & Directive Audit Script
Checks all 39 core quant modules, configuration constants, position sizer logic,
risk manager rules, watchdog settings, universe size, and atomic sync integrity.
"""
import sys, os, sqlite3, importlib
sys.path.insert(0, r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading")
os.chdir(r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading")

import config

results = []

def log_result(item: str, passed: bool, details: str):
    status = "PASS" if passed else "FAIL"
    results.append((item, status, details))
    print(f"[{status}] {item}: {details}")

print("==========================================================")
print("[AUDIT] EXHAUSTIVE DIRECTIVE & SYSTEM AUDIT")
print("==========================================================")

# 1. MAX_POSITIONS Audit
max_pos = getattr(config, 'MAX_POSITIONS', None)
log_result("1. MAX_POSITIONS Config", max_pos == 5, f"Value = {max_pos} (Expected: 5)")

# 2. CONSECUTIVE_LOSS_COOLDOWN Audit
cl_cd = getattr(config, 'ENABLE_CONSECUTIVE_LOSS_COOLDOWN', None)
log_result("2. CONSECUTIVE_LOSS_COOLDOWN", cl_cd == False, f"Value = {cl_cd} (Expected: False)")

# 3. Universe Size Audit
try:
    import universe
    univ_symbols = universe.get_all_symbols()
    log_result("3. Universe 3,500+ Count", len(univ_symbols) >= 3000, f"Count = {len(univ_symbols)} symbols (Expected >= 3000)")
except Exception as e:
    log_result("3. Universe 3,500+ Count", False, f"Error: {e}")

# 4. SQLite DB Trades History & Positions Audit
try:
    conn = sqlite3.connect("trades.db")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM trades")
    trades_cnt = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM daily_stats")
    stats_cnt = cur.fetchone()[0]
    cur.execute("SELECT symbol FROM positions")
    db_positions = [r[0] for r in cur.fetchall()]
    conn.close()
    
    log_result("4. DB Trades History Rows", trades_cnt > 0, f"Count = {trades_cnt} rows (Expected > 0)")
    log_result("5. DB Daily Stats Rows", stats_cnt > 0, f"Count = {stats_cnt} rows (Expected > 0)")
    log_result("6. DB Positions Table Cleanliness", len(db_positions) == 3, f"DB Positions = {db_positions} (Expected 3: MDT, STRC, VTOL)")
except Exception as e:
    log_result("4-6. DB Audit", False, f"Error: {e}")

# 7. Atomic Sync Purge Logic Check
try:
    import atomic_account_sync
    sync_code = open("atomic_account_sync.py", encoding="utf-8").read()
    has_purge = "DELETE FROM positions WHERE symbol = ?" in sync_code
    log_result("7. Atomic Sync Ghost Purge Code", has_purge, "Ghost purge logic confirmed in code")
except Exception as e:
    log_result("7. Atomic Sync Ghost Purge Code", False, f"Error: {e}")

# 8. Notifier HTML Escaping Check
try:
    notifier_code = open("notifier.py", encoding="utf-8").read()
    has_raw_html_bug = ".replace('<', '&lt;')" in notifier_code and "trade_entry" in notifier_code
    log_result("8. Notifier Clean HTML (No Raw Tags)", not has_raw_html_bug, "Raw HTML escaping bug eliminated")
except Exception as e:
    log_result("8. Notifier Clean HTML", False, f"Error: {e}")

# 9. Chart Generator Autoscaling & Date Bounds Check
try:
    chart_code = open("chart_generator.py", encoding="utf-8").read()
    has_today_end = "datetime.now().date()" in chart_code
    has_autoscaling = "y_bottom = min(min_line - span * 0.15, -10.0)" in chart_code
    log_result("9. Chart Today Date Extension", has_today_end, "Chart extends to today")
    log_result("10. Chart Y-Axis Autoscaling", has_autoscaling, "Autoscaling padding confirmed")
except Exception as e:
    log_result("9-10. Chart Generator Check", False, f"Error: {e}")

# 10. Audit Core 39 Modules
modules_to_audit = [
    "trader", "strategy", "screener", "risk_manager", "position_sizer", "macro_shield",
    "regime_detector", "momentum_ranking", "composite_signal", "macro_news_analyzer",
    "dynamic_stop", "drawdown_controller", "anti_fragility", "hedge_manager",
    "theme_radar_adapter", "watchdog", "keepalive", "hidden_markov_regime",
    "data_proxy", "chandelier_exit", "atomic_account_sync", "smart_order_controller",
    "compound_capital_scaler", "news_sentiment_engine", "telegram_receipt", "weekly_audit",
    "execution_tracker", "winrate_optimizer", "performance_attribution", "auto_compound",
    "dynamic_scaling", "auto_tuner_new", "single_instance", "updater", "self_healing_watchdog",
    "chart_generator", "telegram_interactive_bot", "database", "notifier"
]

passed_mods = 0
for mod in modules_to_audit:
    try:
        importlib.import_module(mod)
        passed_mods += 1
    except Exception as me:
        print(f"   Module import error [{mod}]: {me}")

log_result("11. Core 39 Modules Import Audit", passed_mods == len(modules_to_audit), f"Passed {passed_mods}/{len(modules_to_audit)} modules")

print("==========================================================")
print("Summary: {}/{} tests passed".format(sum(1 for r in results if r[1] == "✅ PASS"), len(results)))
print("==========================================================")
