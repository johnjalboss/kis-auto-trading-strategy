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
        print("⚠️ [remote_watchdog.py] Fallback triggered:", err)


def run():
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    restart_count = 0


    while restart_count < MAX_RESTARTS:
        start_time = datetime.now()
        try:
            print(f"[WATCHDOG] Starting main.py (restart #{restart_count})")
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
            error_msg = str(e)

        runtime = (datetime.now() - start_time).total_seconds()
        restart_count += 1

        if exit_code == 0:
            send_tg(f"⚪ <b>트레이딩봇 정상 종료</b>\n실행시간: {runtime/3600:.1f}h")
            break

        send_tg(
            f"🔴 <b>트레이딩봇 크래시!</b>\n"
            f"Exit code: {exit_code}\n"
            f"실행시간: {runtime/3600:.1f}h\n"
            f"재시작: #{restart_count}/{MAX_RESTARTS}\n"
            f"시간: {datetime.now().strftime('%H:%M:%S')}\n"
            f"{RESTART_DELAY}초 후 재시작..."
        )

        if runtime < 10:
            RESTART_DELAY_ACTUAL = min(RESTART_DELAY * restart_count, 300)
            print(f"[WATCHDOG] Crashed too fast, waiting {RESTART_DELAY_ACTUAL}s")
            time.sleep(RESTART_DELAY_ACTUAL)
        else:
            restart_count = max(0, restart_count - 1)
            time.sleep(RESTART_DELAY)

    if restart_count >= MAX_RESTARTS:
        send_tg(f"🚨 <b>트레이딩봇 재시작 한도 초과!</b>\n{MAX_RESTARTS}회 재시작 실패. 수동 확인 필요.")


if __name__ == "__main__":
    run()
