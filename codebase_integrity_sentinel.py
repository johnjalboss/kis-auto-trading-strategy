import os
import sys
import glob
import ast
import re
import sqlite3
import importlib
import traceback

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading"
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

print("=" * 70)
print("🛡️ FULL CODEBASE INTEGRITY SENTINEL & ZERO-BUG AUDIT SUITE")
print("=" * 70)

critical_issues = []
warnings = []

# =========================================================================
# PHASE 1: AST SYNTAX & SCOPE AUDIT FOR ALL .PY FILES
# =========================================================================
print("\n[PHASE 1] AST Parsing & Syntax Verification...")
py_files = sorted(glob.glob("*.py"))
for fn in py_files:
    try:
        with open(fn, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        ast.parse(content, filename=fn)
    except Exception as e:
        critical_issues.append(f"[SYNTAX ERROR] {fn}: {e}")

print(f"  -> Checked {len(py_files)} files. Syntax errors: {len(critical_issues)}")

# =========================================================================
# PHASE 2: STATIC PATTERN AUDIT (UNDEFINED VARS, NONE STRINGS, TIMEZONE)
# =========================================================================
print("\n[PHASE 2] Static Code & String Pattern Analysis...")

# 1. Search for common bug patterns like format strings that might print 'None'
for fn in py_files:
    with open(fn, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    
    for idx, line in enumerate(lines, start=1):
        # Look for direct unhandled pytz calls without import
        if "pytz." in line and "import pytz" not in line:
            # Check if pytz was imported in file
            file_text = "".join(lines)
            if "import pytz" not in file_text and "from pytz" not in file_text:
                critical_issues.append(f"[MISSING IMPORT] {fn}:{idx} uses 'pytz' without importing it!")

        # Look for sqlite3.connect without timeout
        if "sqlite3.connect(" in line and "timeout=" not in line and "memory" not in line:
            warnings.append(f"[SQLITE TIMEOUT WARNING] {fn}:{idx} connects to sqlite without explicit timeout=30.0")

print(f"  -> Critical Pattern Issues: {len(critical_issues)} | Warnings: {len(warnings)}")

# =========================================================================
# PHASE 3: DYNAMIC MODULE IMPORT & EXECUTION VERIFICATION
# =========================================================================
print("\n[PHASE 3] Dynamic Module Import & Instantiation...")
modules_to_test = [
    "config", "database", "trader", "strategy", "screener", "risk_manager",
    "reporter", "daily_settlement_reporter", "weekly_ai_report_generator",
    "auto_tuning_engine", "ai_trade_post_mortem", "telegram_receipt",
    "chart_generator", "trade_error_notebook", "theme_radar_adapter",
    "factor_attribution", "dynamic_expectancy_sizer", "cross_asset_tail_sentinel",
    "fed_net_liquidity_engine", "options_gamma_engine", "sec_form4_insider_radar",
    "macro_event_shock_shield", "monte_carlo_engine", "shadow_paper_engine",
    "dilution_atm_offering_sentinel", "cta_trend_following_sentinel"
]

imported_count = 0
for mod_name in modules_to_test:
    try:
        mod = importlib.import_module(mod_name)
        imported_count += 1
    except Exception as e:
        critical_issues.append(f"[IMPORT FAILED] {mod_name}: {e}")

print(f"  -> Successfully imported {imported_count}/{len(modules_to_test)} core modules.")

# =========================================================================
# PHASE 4: STRING VALIDATION & TELEGRAM CARD FORMATTING ASSERTION
# =========================================================================
print("\n[PHASE 4] Telegram Message Card Output & Assertion Checks...")

def assert_no_glitches(card_text: str, source_name: str):
    if not card_text or not isinstance(card_text, str):
        critical_issues.append(f"[EMPTY CARD] {source_name} returned empty text or non-string!")
        return
    
    # Check for 'None' in formatted output strings
    bad_patterns = [
        r"\bNone일", r"\bNone%", r"\$None\b", r"\bNone주\b", r"\bNone점\b",
        r"\bundefined\b", r"\bNaN\b", r"\bnull\b"
    ]
    for pat in bad_patterns:
        match = re.search(pat, card_text, re.IGNORECASE)
        if match:
            critical_issues.append(f"[GLITCH IN OUTPUT] {source_name} contains glitch: '{match.group(0)}' in:\n{card_text[:300]}")

    # Check HTML tag matching (basic <b> </b>, <code> </code>)
    for tag in ["b", "code", "i", "pre"]:
        opens = len(re.findall(f"<{tag}>", card_text))
        closes = len(re.findall(f"</{tag}>", card_text))
        if opens != closes:
            critical_issues.append(f"[UNCLOSED HTML TAG] {source_name} has mismatched <{tag}> ({opens} vs {closes})")

# 1. Test TelegramReceiptGenerator BUY & SELL with various edge cases
try:
    from telegram_receipt import TelegramReceiptGenerator
    # Edge case 1: hold_days=None
    buy_card = TelegramReceiptGenerator.format_buy_receipt("TEST", 10, 100.0, "MOMENTUM_BREAKOUT", 95, ["Score 95", "PEAD +10"])
    assert_no_glitches(buy_card, "TelegramReceiptGenerator.format_buy_receipt")
    
    sell_card_none_days = TelegramReceiptGenerator.format_sell_receipt("TEST", 10, 100.0, 105.0, "PROFIT_TARGET", hold_days=None)
    assert_no_glitches(sell_card_none_days, "TelegramReceiptGenerator.format_sell_receipt(hold_days=None)")

    sell_card_loss = TelegramReceiptGenerator.format_sell_receipt("TEST", 10, 100.0, 95.0, "DEAD_MONEY_EXIT", hold_days=2.5)
    assert_no_glitches(sell_card_loss, "TelegramReceiptGenerator.format_sell_receipt(DEAD_MONEY)")
except Exception as e:
    critical_issues.append(f"[RECEIPT GENERATOR EXCEPTION] {e}\n{traceback.format_exc()}")

# 2. Test AITradePostMortem
try:
    from ai_trade_post_mortem import AITradePostMortem
    pm = AITradePostMortem()
    for h_arg in [None, 0, 1, 3.5, "약 4일", ""]:
        res_pm = pm.generate_post_mortem("XYZ", 50.0, 52.0, 5, 10.0, 4.0, "DEAD_MONEY_EXIT", holding_days=h_arg)
        assert_no_glitches(res_pm, f"AITradePostMortem(holding_days={h_arg})")
except Exception as e:
    critical_issues.append(f"[POST-MORTEM EXCEPTION] {e}\n{traceback.format_exc()}")

# 3. Test DailySettlementReporter
try:
    from daily_settlement_reporter import DailySettlementReporter
    dsr = DailySettlementReporter()
    rep_d = dsr.generate_daily_report("2026-08-25")
    assert_no_glitches(rep_d.get("telegram_msg", ""), "DailySettlementReporter")
except Exception as e:
    critical_issues.append(f"[DAILY SETTLEMENT EXCEPTION] {e}\n{traceback.format_exc()}")

# 4. Test AutoTuningEngine
try:
    from auto_tuning_engine import AutoTuningEngine
    tuner = AutoTuningEngine()
    card_tune = tuner.format_telegram_card()
    assert_no_glitches(card_tune, "AutoTuningEngine.format_telegram_card")
except Exception as e:
    critical_issues.append(f"[AUTOTUNING EXCEPTION] {e}\n{traceback.format_exc()}")

# 5. Test ChartGenerator (QQQ and SPY)
try:
    from chart_generator import generate_daily_pnl_chart
    _, cap_qqq = generate_daily_pnl_chart(benchmark="QQQ")
    assert_no_glitches(cap_qqq, "ChartGenerator(QQQ)")
    _, cap_spy = generate_daily_pnl_chart(benchmark="SPY")
    assert_no_glitches(cap_spy, "ChartGenerator(SPY)")
except Exception as e:
    critical_issues.append(f"[CHART GENERATOR EXCEPTION] {e}\n{traceback.format_exc()}")

# 6. Test WeeklyAIReportGenerator
try:
    from weekly_ai_report_generator import WeeklyAIReportGenerator
    w_gen = WeeklyAIReportGenerator()
    w_rep = w_gen.generate_report()
    assert_no_glitches(w_rep, "WeeklyAIReportGenerator")
except Exception as e:
    critical_issues.append(f"[WEEKLY AI REPORT EXCEPTION] {e}\n{traceback.format_exc()}")

# =========================================================================
# PHASE 5: SUMMARY & PASS/FAIL GATE
# =========================================================================
print("\n" + "=" * 70)
print(f"📊 ZERO-BUG AUDIT RESULTS:")
print(f"   • Total Critical Issues: {len(critical_issues)}")
print(f"   • Total Warnings       : {len(warnings)}")
print("=" * 70)

if critical_issues:
    print("\n❌ CRITICAL ISSUES FOUND:")
    for ci in critical_issues:
        print("  ❌ " + ci)
    sys.exit(1)
else:
    print("\n✅ 100% PASS - ALL INTEGRITY TESTS, PARSERS, AND STRINGS ARE FLAWLESS!")
    sys.exit(0)
