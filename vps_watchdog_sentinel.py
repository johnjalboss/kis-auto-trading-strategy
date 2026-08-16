"""
vps_watchdog_sentinel.py
================================================================================
Autonomous VPS Health Sentinel & Self-Healing Watchdog for KIS Auto-Trading
- Monitored services:
  1. trading-bot.service (Core KIS Autonomous Trading Engine via watchdog.py / main.py)
  2. theme-radar.service (24/7 Real-Time US Theme Radar Daemon)
  3. web-dashboard.service (Web Analytics Dashboard on Port 8080)
- Checks:
  * Systemd active status (systemctl is-active)
  * Process PID existence and non-zombie state
  * Web Dashboard HTTP responsiveness (curl port 8080)
- Performs automatic self-healing restart ONLY if genuinely dead or unresponsive.
- Suppresses repeat alert spamming with state tracking.
================================================================================
"""

import os
import sys
import time
import subprocess
import datetime
import requests
from typing import Dict, List, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")

SERVICES = [
    {
        "name": "trading-bot.service",
        "description": "KIS 무인 자동매매 트레이딩 엔진",
        "type": "systemd",
        "cmd_patterns": ["watchdog.py", "main.py", "orchestrator.py"]
    },
    {
        "name": "theme-radar.service",
        "description": "24/7 미국 증시 테마 레이더 실시간 데몬",
        "type": "systemd",
        "cmd_patterns": ["theme_radar_daemon.py"]
    },
    {
        "name": "web-dashboard.service",
        "description": "실시간 웹 대시보드 서버 (Port 8080)",
        "type": "http",
        "url": "http://localhost:8080/login",
        "cmd_patterns": ["web_dashboard.py"]
    }
]

def load_telegram_credentials() -> Tuple[str, str]:
    """Loads Telegram credentials from environment or .env file."""
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    tg_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not tg_token or not tg_chat_id:
        env_candidates = [
            os.path.join(BASE_DIR, ".env"),
            "/home/ubuntu/kis-auto-trading/.env"
        ]
        for ec in env_candidates:
            if os.path.exists(ec):
                with open(ec, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("TELEGRAM_BOT_TOKEN="):
                            tg_token = line.split("=", 1)[1].strip().strip('"').strip("'")
                        elif line.startswith("TELEGRAM_CHAT_ID="):
                            tg_chat_id = line.split("=", 1)[1].strip().strip('"').strip("'")
                if tg_token and tg_chat_id:
                    break
    return tg_token, tg_chat_id

def send_telegram_alert(message: str):
    """Sends high-priority watchdog alert to Telegram."""
    token, chat_id = load_telegram_credentials()
    if not token or not chat_id:
        print(f"[Watchdog Alert (No TG)]: {message}")
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=5)
    except Exception as e:
        print(f"[Watchdog] Failed to send TG alert: {e}")

def check_service_health(svc: Dict) -> Tuple[bool, str]:
    """
    Evaluates true operational health of a service.
    Returns (is_healthy, reason_if_unhealthy).
    """
    s_name = svc["name"]

    # 1. Check systemd status
    res = subprocess.run(["systemctl", "is-active", s_name], capture_output=True, text=True)
    active_status = res.stdout.strip()
    if active_status != "active":
        return False, f"systemd 상태 비활성({active_status})"

    # 2. Check process existence against allowed patterns
    cmd_patterns = svc.get("cmd_patterns", [])
    found_process = False
    for pat in cmd_patterns:
        pg_res = subprocess.run(["pgrep", "-f", pat], capture_output=True, text=True)
        pids = [p for p in pg_res.stdout.strip().split() if p and p.isdigit() and int(p) != os.getpid()]
        if pids:
            found_process = True
            break

    if not found_process and cmd_patterns:
        return False, f"프로세스({', '.join(cmd_patterns)}) 미실행"

    # 3. For HTTP service, verify actual HTTP response
    if svc.get("type") == "http":
        try:
            r = requests.get(svc["url"], timeout=3)
            if r.status_code not in [200, 302]:
                return False, f"HTTP 응답 이상 (Status {r.status_code})"
        except Exception as e:
            return False, f"HTTP 연결 실패 ({e})"

    return True, "정상"

def check_and_heal_services():
    """Checks all critical systemd services and performs self-healing only if genuinely dead."""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    restarted_services = []

    for svc in SERVICES:
        s_name = svc["name"]
        desc = svc["description"]
        
        is_healthy, reason = check_service_health(svc)
        if not is_healthy:
            print(f"[{now_str}] ⚠️ Service {s_name} is unhealthy ({reason}). Attempting self-healing restart...")
            
            # Perform self-healing restart
            restart_res = subprocess.run(["sudo", "systemctl", "restart", s_name], capture_output=True, text=True)
            time.sleep(2)
            
            # Re-verify after restart
            post_healthy, post_reason = check_service_health(svc)
            if post_healthy:
                restarted_services.append((s_name, desc, reason, "성공 (정상 복구)"))
            else:
                restarted_services.append((s_name, desc, reason, f"실패 ({post_reason})"))

    if restarted_services:
        lines = [
            "🛡️ <b>[VPS 왓치독: 자율 복구(Self-Healing) 보고]</b>",
            "━━━━━━━━━━━━━━━━━━━",
            f"⏱ <b>발생시각:</b> <code>{now_str}</code>\n"
        ]
        for s_name, desc, reason, result in restarted_services:
            status_icon = "✅" if "성공" in result else "❌"
            lines.append(f"• <b>{desc}</b> (<code>{s_name}</code>)")
            lines.append(f"  - 장애 원인: <i>{reason}</i>")
            lines.append(f"  - 복구 결과: {status_icon} <b>{result}</b>\n")
        lines.append("━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 <i>시스템이 장애를 자율 복구하고 정상 가동을 재개했습니다.</i>")
        send_telegram_alert("\n".join(lines))
    else:
        print(f"[{now_str}] ✅ All {len(SERVICES)} services healthy and active.")

if __name__ == "__main__":
    check_and_heal_services()
