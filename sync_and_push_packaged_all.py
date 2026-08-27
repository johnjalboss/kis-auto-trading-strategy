import os, sys, shutil, subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

src_dir = r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading"
dst_dir = r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading-packaged"

print("==========================================================")
print("🛡️ [PRE-FLIGHT] RUNNING ZERO-BUG INTEGRITY AUDIT GATE")
print("==========================================================")
sentinel_res = subprocess.run([sys.executable, "codebase_integrity_sentinel.py"], cwd=src_dir)
if sentinel_res.returncode != 0:
    print("\n❌ [CRITICAL] PRE-FLIGHT INTEGRITY AUDIT FAILED! DEPLOYMENT ABORTED TO PREVENT PRODUCTION BUGS.")
    sys.exit(1)
print("\n✅ PRE-FLIGHT INTEGRITY AUDIT 100% PASSED! PROCEEDING WITH SYNC & DEPLOY...\n")

print("==========================================================")
print("[SYNC] SYNCING LOCAL CODE TO PACKAGED FRIEND DISTRIBUTION")
print("==========================================================")

files_to_sync = [
    "fed_net_liquidity_engine.py",
    "options_gamma_engine.py",
    "sec_form4_insider_radar.py",
    "macro_event_shock_shield.py",
    "winrate_optimizer.py",
    "pre_market_gap_sentinel.py",
    "database.py",
    "web_dashboard.py",
    "trade_error_notebook.py",
    "cross_sectional_momentum.py",
    "vpin_microstructure.py",
    "volatility_sizer.py",
    "pead_earnings_radar.py",
    "auto_tuning_engine.py",
    "hurst_fractal_regime.py",
    "amihud_liquidity_pressure.py",
    "dynamic_ratchet_take_profit.py",
    "cross_asset_tail_sentinel.py",
    "residual_momentum_alpha.py",
    "order_flow_tick_momentum.py",
    "chandelier_exit.py",
    "portfolio_decorrelation.py",
    "dynamic_expectancy_sizer.py",
    "factor_attribution.py",
    "volume_profile_poc.py",
    "macro_event_shield.py",
    "opening_range_breakout.py",
    "kalman_trend_filter.py",
    "leader_pyramiding_engine.py",
    "vcp_breakout_engine.py",
    "account_high_water_mark_sentinel.py",
    "db_maintenance_guard.py",
    "daily_settlement_reporter.py",
    "weekly_ai_report_generator.py",
    "shadow_paper_engine.py",
    "macro_event_horizon.py",
    "ai_trade_post_mortem.py",
    "smart_money_footprint.py",
    "smart_pegged_router.py",
    "monte_carlo_engine.py",
    "multi_timeframe_confluence.py",
    "config.py",
    "reporter.py",
    "notification.py",
    "chart_generator.py",
    "orchestrator.py",
    "telegram_receipt.py",
    "telegram_interactive_bot.py",
    "strategy.py",
    "sector_rotator.py",
    "screener.py",
    "composite_signal.py",
    "trader.py",
    "kis_data.py",
    "kis_symbol_blacklist.json",
    "smart_order.py",
    "main.py",
    "fetch_dashboard_data.py",
    "position_sizer.py",
    "risk_manager.py",
    "deploy.py",
    "theme_radar_adapter.py",
    "test_4_new_quant_engines.py",
    "codebase_integrity_sentinel.py"
]

copied_count = 0
for fname in files_to_sync:
    src_f = os.path.join(src_dir, fname)
    dst_f = os.path.join(dst_dir, fname)
    if os.path.exists(src_f):
        shutil.copy2(src_f, dst_f)
        copied_count += 1
        print(f"  [OK] Copied {fname} to packaged dir")
    else:
        print(f"  [SKIP] {fname} not found in src_dir")

print(f"\nTotal Files Synced to Packaged Dir: {copied_count}")

# Copy updated us-theme-tracker files
src_theme_daemon = r"C:\Users\wngud\.gemini\antigravity\scratch\us-theme-tracker\theme_radar_daemon.py"
dst_theme_daemon = r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading-packaged\us-theme-tracker\theme_radar_daemon.py"
if os.path.exists(src_theme_daemon) and os.path.exists(os.path.dirname(dst_theme_daemon)):
    shutil.copy2(src_theme_daemon, dst_theme_daemon)
    print("  [OK] Copied us-theme-tracker/theme_radar_daemon.py to packaged dir")

# Git Commit & Push in kis-auto-trading
try:
    print("\nGit Status & Push in kis-auto-trading:")
    subprocess.run(["git", "add", "."], cwd=src_dir, check=True)
    subprocess.run(["git", "commit", "-m", "v2026.08.14 Institutional AutoTuning & Day Zero Fresh Baseline Engine"], cwd=src_dir, check=False)
    res_push = subprocess.run(["git", "push", "origin", "main"], cwd=src_dir, capture_output=True, text=True)
    print("Push Output:", res_push.stdout or res_push.stderr)
except Exception as ge:
    print("Git Push Warning:", ge)

# Git Commit & Push in kis-auto-trading-packaged if git exists there
if os.path.exists(os.path.join(dst_dir, ".git")):
    try:
        print("\nGit Status & Push in kis-auto-trading-packaged:")
        subprocess.run(["git", "add", "."], cwd=dst_dir, check=True)
        subprocess.run(["git", "commit", "-m", "v2026.08.14 Friend Distribution AutoTuning Release"], cwd=dst_dir, check=False)
        res_push_pkg = subprocess.run(["git", "push", "origin", "main"], cwd=dst_dir, capture_output=True, text=True)
        print("Packaged Push Output:", res_push_pkg.stdout or res_push_pkg.stderr)
    except Exception as pge:
        print("Packaged Git Push Warning:", pge)

print("==========================================================")
