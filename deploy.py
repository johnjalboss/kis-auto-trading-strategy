"""
배포 스크립트: 로컬 → VPS 자동 배포
사용법: python deploy.py [파일명1 파일명2 ...]
  - 인자 없으면 CORE_FILES 전체 배포
  - 배포 후 main.py / web_dashboard.py 자동 재시작
"""
import subprocess, sys, time

KEY = 'id_rsa'
SERVER = 'ubuntu@141.148.172.12'
REMOTE_DIR = '/home/ubuntu/kis-auto-trading'

CORE_FILES = [
    "main.py",
    "telegram_interactive_bot.py",
    "web_dashboard.py",
    "orchestrator.py",
    "trader.py",
    "strategy.py",
    "screener.py",
    "risk_manager.py",
    "config.py",
    "database.py",
    "notifier.py",
    "scheduler.py",
    "kis_client.py",
    "kis_data.py",
    "position_sizer.py",
    "smart_order.py",
    "macro_shield.py",
    "regime_detector.py",
    "momentum_ranking.py",
    "composite_signal.py",
    "macro_news_analyzer.py",
    "dynamic_stop.py",
    "drawdown_controller.py",
    "anti_fragility.py",
    "hedge_manager.py",
    "theme_radar_adapter.py",
    "watchdog.py",
    "keepalive.py",
    "hidden_markov_regime.py",
    "data_proxy.py",
    "chandelier_exit.py",
    "atomic_account_sync.py",
    "smart_order_controller.py",
    "compound_capital_scaler.py",
    "news_sentiment_engine.py",
    "telegram_receipt.py",
    "weekly_audit.py",
    "safe_math.py",
    "adaptive_vix_engine.py",
    "mtf_confluence_filter.py",
    "gamma_squeeze_radar.py",
    "risk_parity_allocator.py",
    "cross_asset_momentum.py",
    "order_flow_imbalance.py",
]

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr

def scp_file(fname):
    code, out = run(['scp', '-i', KEY, '-o', 'StrictHostKeyChecking=no',
                     '-o', 'ConnectTimeout=15', fname, f'{SERVER}:{REMOTE_DIR}/{fname}'])
    if code == 0:
        print(f"  [OK] {fname}")
    else:
        print(f"  [FAIL] {fname}: {out.strip()}")
    return code == 0

def ssh_cmd(cmd):
    code, out = run(['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', SERVER, cmd])
    return code, out

def restart_services():
    print("\n[RESTART] Restarting services cleanly on VPS...")

    # 1. 모든 기존 프로세스 완전 강제 종료 (kill -9) & 락 파일/캐시 소거
    clean_cmd = (
        "pkill -9 -f watchdog.py ; "
        "pkill -9 -f main.py ; "
        "pkill -9 -f web_dashboard.py ; "
        "rm -f /tmp/kis_auto_trading.lock /tmp/*.lock ; "
        f"find {REMOTE_DIR} -name '__pycache__' -exec rm -rf {{}} + 2>/dev/null || true ; "
        "sleep 2"
    )
    ssh_cmd(clean_cmd)
    time.sleep(2)

    # 2. 메인 봇 & 웹 대시보드 100% 신규 인스턴스 1개씩 깔끔하게 구동
    ssh_cmd(f"cd {REMOTE_DIR} && nohup venv/bin/python main.py >> logs/trading.log 2>&1 &")
    time.sleep(3)
    ssh_cmd(f"fuser -k 8080/tcp 2>/dev/null || true ; cd {REMOTE_DIR} && nohup venv/bin/python web_dashboard.py >> logs/dashboard.log 2>&1 &")
    time.sleep(3)

    # 3. 메인 프로세스 검증
    code, out = ssh_cmd("pgrep -a -f 'main.py'")
    pids = out.strip()
    if pids:
        print(f"  [OK] main.py cleanly restarted: {pids}")
    else:
        print("  [FAIL] main.py failed to start")

    # 4. 웹 대시보드 검증
    code, out = ssh_cmd("pgrep -a -f 'web_dashboard.py'")
    pids_dash = out.strip()
    if pids_dash:
        print(f"  [OK] web_dashboard.py cleanly restarted: {pids_dash}")
    else:
        print("  [WARN] web_dashboard.py check failed")

if __name__ == '__main__':
    files = sys.argv[1:] if len(sys.argv) > 1 else CORE_FILES
    print(f"[DEPLOY] Target files count: {len(files)} -> {SERVER}:{REMOTE_DIR}")
    ok = 0
    for f in files:
        import os
        if os.path.exists(f):
            if scp_file(f):
                ok += 1
        else:
            print(f"  [SKIP] {f} (not found locally)")

    print(f"\n[DEPLOY] Completed: {ok}/{len(files)}")

    if '--no-restart' not in sys.argv:
        restart_services()
    else:
        print("[INFO] --no-restart flag passed, skipping restart")
