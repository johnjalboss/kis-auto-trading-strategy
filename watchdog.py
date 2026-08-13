"""
Watchdog - Auto-restart + Telegram crash alerts
Oracle Cloud 24/7 unattended operation
"""
import os, sys, time, subprocess, requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
MAX_RESTARTS = 100
RESTART_DELAY = 30


def send_tg(msg):
    if not TOKEN or not CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except Exception as err:
        print("⚠️ [watchdog.py] Fallback triggered:", err)


def is_main_running() -> bool:
    """main.py가 이미 실행 중인지 확인 (중복 실행 방지)"""
    try:
        my_pid = os.getpid()
        res = subprocess.run("pgrep -f 'main.py'", shell=True, capture_output=True, text=True)
        pids = [int(p.strip()) for p in res.stdout.strip().split('\n') if p.strip().isdigit()]
        pids = [p for p in pids if p != my_pid]
        return len(pids) > 0
    except Exception:
        return False


def run():
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    restart_count = 0

    while True:
        # 이미 main.py가 정상 작동 중인 경우 중복 구동하지 않고 모니터링만 수행
        if is_main_running():
            time.sleep(30)
            continue

        start_time = datetime.now()
        try:
            print(f"[WATCHDOG] Starting main.py daemon (restart #{restart_count})")
            python_exe = sys.executable if sys.executable else "python3"
            proc = subprocess.run(
                [python_exe, script],
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            exit_code = proc.returncode
        except KeyboardInterrupt:
            send_tg("🔴 <b>트레이딩봇 수동 종료</b>")
            print("[WATCHDOG] Manual shutdown")
            sys.exit(0)
        except Exception as e:
            exit_code = -1

        runtime = (datetime.now() - start_time).total_seconds()

        # 정상 종료 시 (예: 배포/업데이트 시)
        if exit_code == 0:
            if runtime > 60:
                send_tg(f"⚪ <b>트레이딩봇 사이클 정상 마감</b>\n실행시간: {runtime/3600:.1f}h\n10초 후 지속 가동...")
            time.sleep(10)
            continue

        restart_count += 1
        send_tg(
            f"🔴 <b>트레이딩봇 종료 / 크래시 경보!</b>\n"
            f"Exit code: {exit_code}\n"
            f"실행시간: {runtime/3600:.1f}h\n"
            f"재시작: #{restart_count}\n"
            f"시간: {datetime.now().strftime('%H:%M:%S')}\n"
            f"10초 후 자동 재가동 진행 중..."
        )
        time.sleep(10)


if __name__ == "__main__":
    run()
