import os
import glob

# =================================================================
# [안전 가드] 절대 보존 파일 (Swing Bot 구동 필수 파일)
# =================================================================
PROTECTED_FILES = {
    # 1. 코어 매매 시스템
    "main.py", "trader.py", "strategy.py", "orchestrator.py", "screener.py", "indicators.py", "utils.py",
    "kis_client.py", "kis_data.py", "auth.py", "data_proxy.py",
    "risk_manager.py", "position_sizer.py", "drawdown_controller.py", "frequency_controller.py", "emergency_stop.py", "kelly_criterion.py",
    "telegram_commander.py", "notifier.py", "notification.py",
    "composite_signal.py", "macro.py", "regime_detector.py",
    # 2. 수급 및 매크로 모듈
    "fed_watch.py", "smart_money.py", "etf_flows.py", "insider_tracker.py",
    "chart_generator.py",
    # 3. 중요 데이터베이스 및 설정 (절대 보호)
    "trades.db", "server_trades.db", "server_trade_journal.db", "trade_journal.db", "trading.db",
    ".env", "id_rsa", "oracle_key", "version.json", "requirements.txt", "updater.py",
    # 4. 배포 스크립트
    "deploy_all.py", "deploy_v106.py"
}

# =================================================================
# 삭제 대상 명시적 파일 목록
# =================================================================
DELETE_LIST = [
    # 단타/스캘핑 obsolete 전략
    "intraday_momentum.py", "premarket_gap.py", "high_frequency_backtest.py", "competition_mode.py", "check_mrvl_dawn.py",
    # 서비스 템플릿
    "kis-trading.service", "kis-trading.service.final", "kis-trading.service.final2", "kis-trading.service.new",
    "local_kis-trading.service", "local_kis-trading.service.utf8", "trading-bot.service",
    # 임시 txt 리포트, 출력물, 덤프
    "temp_out.txt", "test_out.txt", "test2.out", "sys_one.txt", "sys_restarts.txt", "sys_status.txt",
    "tail_err_log.txt", "ticker_results.txt", "xom3_today.txt", "xom_log.txt", "xom_today.txt",
    "truly_ultimate_results.txt", "ultimate_results.txt", "signatures.txt",
    "audit_results.txt", "audit_output.txt", "verify_output.txt", "trade_analysis_raw.txt",
    "latest_tail.txt", "restarts.txt", "report_verify.txt", "trace_output.txt", "output.txt", "audit_out.txt",
    "ultra_aggressive_results.txt", "multistock_results.txt", "hf_results.txt", "market_beating_results.txt", "diag_pltd_out.txt",
    # 단발성 임시 디버깅 파이썬 스크립트
    "test_comp.py", "test_composite.py", "test_db_dedup.py", "test_signal.py", "test2.py", "test2.out",
    "test_vol.py", "test_sentiment.py", "test_telegram_server.py", "test_report_fix.py", "test_engine_cache.py",
    "test_adapters_fix.py", "test_import.py", "temp_diag.py", "dump.py", "dump_db.py",
    "api_extract.json", "yesterday_trades.json", "temp_fetch.json", "temp_fetch_utf8.json", "temp_fetch_verify.json",
    "temp_dashboard.json", "temp_dashboard2.json", "temp_dashboard_live.json", "fresh_dashboard_data.json", "fetch_out.json",
    "strategy.py.b64", "server_strategy.b64", "server_composite_signal.b64", "server_orchestrator.b64",
    "updates.tar", "test_journal.db", "test_screener.log", "test_screener.log.1"
]

# =================================================================
# 삭제 대상 패턴 (주로 로그 롤백 백업 파일)
# =================================================================
PATTERN_DELETE = [
    "*.log.[0-9]",
    "*.log.[0-9].gz",
    "*.log.gz",
    "*.tar",
    "*.zip"
]

def clean_local():
    print("=" * 60)
    print("Executing Safety Local Garbage Cleanup (v1.1)...")
    print("=" * 60)
    
    deleted = 0
    for filename in DELETE_LIST:
        if filename in PROTECTED_FILES:
            continue
        if os.path.exists(filename):
            try:
                os.remove(filename)
                print(f"[DELETED] -> {filename}")
                deleted += 1
            except Exception as e:
                print(f"[FAIL] -> {filename}: {e}")
                
    for pattern in PATTERN_DELETE:
        for filepath in glob.glob(pattern):
            filename = os.path.basename(filepath)
            if filename in PROTECTED_FILES:
                continue
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    print(f"[DELETED-PATTERN] -> {filename}")
                    deleted += 1
                except Exception as e:
                    print(f"[FAIL-PATTERN] -> {filename}: {e}")
                    
    print("-" * 60)
    print(f"Local cleanup done. Deleted {deleted} files.")
    print("=" * 60)

if __name__ == "__main__":
    clean_local()
