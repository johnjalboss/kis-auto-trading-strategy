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


def run():
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    restart_count = 0


    while True:
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

        # 정상 종료(exit_code == 0)시 텔레그램 스팸 알림 없이 10초 후 24시간 무한 자동 재가동
        if exit_code == 0:
            print(f"[WATCHDOG] main.py completed cycle (runtime: {runtime:.1f}s). Restarting in 10s...")
            time.sleep(10)
            continue

        restart_count += 1
        send_tg(
            f"🔴 <b>트레이딩봇 재시작 경보</b>\n"
            f"Exit code: {exit_code}\n"
            f"실행시간: {runtime/3600:.1f}h\n"
            f"재시작: #{restart_count}\n"
            f"10초 후 24시간 무한 자동 재가동..."
        )
        time.sleep(10)


if __name__ == "__main__":
    run()
