"""
telegram_commander.py
======================
텔레그램에서 명령어를 입력하면 봇이 실시간으로 응답합니다.

지원 명령어:
  /status   — 봇 상태, 포지션 수, 구매력 요약
  /포지션    — 현재 보유 포지션 상세 (P&L 포함)
  /수익      — 오늘의 실현 손익
  /도움말    — 명령어 목록

오케스트레이터에서 백그라운드 스레드로 실행됩니다.
"""

import os
import time
import threading
import requests
from datetime import datetime
from loguru import logger

try:
    import config
    _TOKEN   = getattr(config, "TELEGRAM_BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", ""))
    _CHAT_ID = getattr(config, "TELEGRAM_CHAT_ID",   os.getenv("TELEGRAM_CHAT_ID",   ""))
except Exception:
    _TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")
    _CHAT_ID = os.getenv("TELEGRAM_CHAT_ID",   "")

_POLL_INTERVAL = 5       # 초 (Telegram getUpdates long-polling)
_TIMEOUT       = 30      # long-polling 대기 초


def _send(text: str, reply_markup: dict = None) -> None:
    if not _TOKEN or not _CHAT_ID:
        return
    try:
        payload = {"chat_id": _CHAT_ID, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        requests.post(
            f"https://api.telegram.org/bot{_TOKEN}/sendMessage",
            json=payload,
            timeout=10,
        )
    except Exception as e:
        logger.debug("Commander send failed: {}", e)


def _send_photo(photo_path: str, caption: str = "") -> None:
    if not _TOKEN or not _CHAT_ID or not photo_path or not os.path.exists(photo_path):
        return
    try:
        with open(photo_path, 'rb') as photo:
            requests.post(
                f"https://api.telegram.org/bot{_TOKEN}/sendPhoto",
                data={"chat_id": _CHAT_ID, "caption": caption, "parse_mode": "HTML"},
                files={"photo": photo},
                timeout=20,
            )
    except Exception as e:
        logger.debug("Commander send_photo failed: {}", e)


def _get_updates(offset: int) -> list:
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{_TOKEN}/getUpdates",
            params={"offset": offset, "timeout": _TIMEOUT, "allowed_updates": ["message", "callback_query"]},
            timeout=_TIMEOUT + 5,
        )
        if resp.ok:
            return resp.json().get("result", [])
    except Exception:
        pass
    return []


# ─────────────────────────────────────────────
# 명령어 핸들러
# ─────────────────────────────────────────────

def _handle_status() -> str:
    lines = ["🤖 <b>봇 상태</b>"]
    lines.append(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    # 일시정지 상태 표시
    if os.path.exists("/tmp/kis_trading_paused"):
        lines.append("🔴 <b>매수 일시정지 중</b> (/재개 로 재개)")
    else:
        lines.append("✅ 정상 가동 중")
    try:
        from trader import get_trader
        trader = get_trader()
        bp = trader.get_buying_power()
        positions = trader.get_positions()
        total_val = bp + sum(getattr(p, 'market_value', 0) for p in positions)
        lines.append(f"💵 구매력: <b>${bp:,.2f}</b>")
        lines.append(f"📦 포지션: <b>{len(positions)}개</b>")
        lines.append(f"💼 총 자산: <b>${total_val:,.2f}</b>")
    except Exception as e:
        lines.append(f"⚠️ 계좌 조회 실패: {e}")
    return "\n".join(lines)


def _handle_positions() -> str:
    try:
        from trader import get_trader
        trader = get_trader()
        positions = trader.get_positions()
        if not positions:
            return "📭 현재 보유 포지션이 없습니다."

        lines = [f"📈 <b>현재 보유 포지션 ({len(positions)}개)</b>"]
        lines.append("━" * 18)
        for p in positions:
            try:
                avg     = getattr(p, 'avg_price', 0)
                cur     = getattr(p, 'current_price', 0)
                qty     = getattr(p, 'quantity', 0)
                sym     = getattr(p, 'symbol', '?')
                pct     = getattr(p, 'pnl_pct', (cur - avg) / avg if avg > 0 else 0)
                pnl_usd = (cur - avg) * qty
                emoji   = "🟢" if pct >= 0 else "🔴"
                lines.append(
                    f"{emoji} <code>{sym:5s}</code> | {qty}주 | "
                    f"${cur:.2f} | {pct:+.1%} (<b>${pnl_usd:+,.2f}</b>)"
                )
            except Exception:
                lines.append(f"⚠️ {getattr(p, 'symbol', '?')} 조회 실패")
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ 포지션 조회 실패: {e}"


def _handle_pnl() -> str:
    try:
        from database import get_database
        import pytz
        us_today = datetime.now(pytz.timezone('US/Eastern')).date()
        db     = get_database()
        trades = db.get_trades_today(us_today)
        sells  = [t for t in (trades or []) if t.side == "SELL"]
        if not sells:
            return f"📭 오늘({us_today}) 실현된 거래가 없습니다."

        total_pnl = sum(t.pnl for t in sells)
        wins      = sum(1 for t in sells if t.pnl > 0)
        emoji     = "💰" if total_pnl >= 0 else "🔻"

        lines = [f"{emoji} <b>오늘의 실현 손익 ({us_today})</b>"]
        lines.append("━" * 18)
        lines.append(f"총 {len(sells)}건 ({wins}승 / {len(sells)-wins}패)")
        lines.append(f"순손익: <b>${total_pnl:+,.2f}</b>")
        lines.append("━" * 18)
        for t in sorted(sells, key=lambda x: x.pnl, reverse=True):
            e = "🟢" if t.pnl >= 0 else "🔴"
            lines.append(f"{e} <code>{t.symbol:5s}</code> <b>${t.pnl:+,.2f}</b> ({t.pnl_pct:+.1%})")
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ 수익 조회 실패: {e}"


def _handle_pause() -> str:
    try:
        with open("/tmp/kis_trading_paused", "w") as f:
            f.write(datetime.now().isoformat())
        return (
            "🔴 <b>매수 일시정지 완료</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• 신규 매수가 즉시 차단됩니다\n"
            "• 보유 포지션 청산은 계속 진행됩니다\n"
            "• /재개 로 다시 활성화하세요"
        )
    except Exception as e:
        return f"⚠️ 일시정지 실패: {e}"


def _handle_resume() -> str:
    try:
        pause_file = "/tmp/kis_trading_paused"
        if os.path.exists(pause_file):
            os.remove(pause_file)
            return (
                "✅ <b>매수 재개 완료</b>\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "• 봇이 정상적으로 신규 매수를 시작합니다"
            )
        else:
            return "ℹ️ 이미 정상 가동 중입니다 (일시정지 상태 아님)"
    except Exception as e:
        return f"⚠️ 재개 실패: {e}"


def _handle_chart(days: int = 90) -> None:
    try:
        from chart_generator import generate_daily_pnl_chart
        # Generate the chart
        chart_path = generate_daily_pnl_chart(days=days)
        if chart_path and os.path.exists(chart_path):
            period_str = "전체 기간" if days <= 0 else f"{days}일"
            _send_photo(chart_path, f"📊 <b>수익 차트 ({period_str})</b>")
        else:
            _send("⚠️ 차트 생성 실패: 거래 데이터를 찾을 수 없거나 차트 생성 중 오류가 발생했습니다.")
    except Exception as e:
        _send(f"⚠️ 차트 생성 중 오류 발생: {e}")


def _handle_chart_90():
    _handle_chart(90)
    return None


def _handle_chart_30():
    _handle_chart(30)
    return None


def _handle_chart_all():
    _handle_chart(0)
    return None


def _handle_help() -> tuple:
    paused = "🔴 일시정지 중" if os.path.exists("/tmp/kis_trading_paused") else "✅ 정상 가동"
    text = (
        f"📋 <b>AI 스윙 봇 인터랙티브 제어판</b> [{paused}]\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "아래의 버튼을 터치하여 실시간 상태 조회, 보유 포지션 확인, 수익 차트 팝업, 매수 제어를 실행할 수 있습니다."
    )
    markup = {
        "inline_keyboard": [
            [
                {"text": "📊 봇 상태 요약", "callback_data": "/status"},
                {"text": "📈 보유 포지션", "callback_data": "/포지션"}
            ],
            [
                {"text": "💰 오늘 실현손익", "callback_data": "/수익"},
                {"text": "📊 90일 수익차트", "callback_data": "/차트"}
            ],
            [
                {"text": "⏸️ 매수 일시정지", "callback_data": "/일시정지"},
                {"text": "▶️ 매수 재개", "callback_data": "/재개"}
            ]
        ]
    }
    return text, markup


_COMMANDS = {
    "/status":   _handle_status,
    "/포지션":   _handle_positions,
    "/수익":     _handle_pnl,
    "/차트":     _handle_chart_90,
    "/차트30":   _handle_chart_30,
    "/차트전체": _handle_chart_all,
    "/차트0":    _handle_chart_all,
    "/chart":    _handle_chart_90,
    "/chart30":  _handle_chart_30,
    "/chartall": _handle_chart_all,
    "/chart0":   _handle_chart_all,
    "/일시정지": _handle_pause,
    "/재개":     _handle_resume,
    "/도움말":   _handle_help,
    "/help":     _handle_help,
}


# ─────────────────────────────────────────────
# 폴링 루프 (백그라운드 스레드)
# ─────────────────────────────────────────────

def _polling_loop() -> None:
    if not _TOKEN or not _CHAT_ID:
        logger.warning("TelegramCommander: TOKEN or CHAT_ID missing — commander disabled")
        return

    logger.info("TelegramCommander started (polling every {}s)", _POLL_INTERVAL)
    offset = 0
    while True:
        try:
            updates = _get_updates(offset)
            for upd in updates:
                offset = upd["update_id"] + 1
                
                # 1. 일반 텍스트 메시지 수신 처리
                msg = upd.get("message", {})
                if msg and str(msg.get("chat", {}).get("id", "")) == str(_CHAT_ID):
                    text = (msg.get("text") or "").strip().lower().split()[0] if msg.get("text") else ""
                    raw = (msg.get("text") or "").strip().split()[0] if msg.get("text") else ""
                    handler = _COMMANDS.get(raw) or _COMMANDS.get(text)
                    if handler:
                        try:
                            reply = handler()
                            if reply:
                                if isinstance(reply, tuple):
                                    _send(reply[0], reply_markup=reply[1])
                                else:
                                    _send(reply)
                        except Exception as e:
                            _send(f"⚠️ 명령 처리 오류: {e}")

                # 2. 인라인 버튼 클릭 신호(Callback Query) 수신 처리
                cb = upd.get("callback_query", {})
                if cb:
                    cb_data = cb.get("data", "")
                    cb_id = cb.get("id", "")
                    chat_id = cb.get("message", {}).get("chat", {}).get("id", "")
                    if str(chat_id) == str(_CHAT_ID) and cb_data:
                        # 클릭 로딩 모래시계 시각적 정지
                        try:
                            requests.post(
                                f"https://api.telegram.org/bot{_TOKEN}/answerCallbackQuery",
                                json={"callback_query_id": cb_id},
                                timeout=5,
                            )
                        except Exception:
                            pass

                        # 버튼 내부 데이터에 대응되는 핸들러 실행
                        handler = _COMMANDS.get(cb_data)
                        if handler:
                            try:
                                reply = handler()
                                if reply:
                                    if isinstance(reply, tuple):
                                        _send(reply[0], reply_markup=reply[1])
                                    else:
                                        _send(reply)
                            except Exception as e:
                                _send(f"⚠️ 명령 처리 오류: {e}")
        except Exception as e:
            logger.debug("TelegramCommander polling error: {}", e)
            time.sleep(_POLL_INTERVAL * 2)

        time.sleep(_POLL_INTERVAL)


def start_commander() -> None:
    """오케스트레이터에서 호출 — 커맨더 + 하트비트 스레드 시작"""
    t = threading.Thread(target=_polling_loop, daemon=True, name="TelegramCommander")
    t.start()
    h = threading.Thread(target=_heartbeat_loop, daemon=True, name="TelegramHeartbeat")
    h.start()
    logger.info("TelegramCommander + Heartbeat threads started")


# ─────────────────────────────────────────────
# 하트비트 감시 (장중에 봇이 죽으면 즉시 알림)
# ─────────────────────────────────────────────

_HEARTBEAT_CHECK_INTERVAL = 600   # 10분마다 로그 확인
_HEARTBEAT_SILENT_LIMIT   = 7200  # 2시간 이상 무활동이면 경보
_LOG_PATHS = [
    "/home/ubuntu/kis-auto-trading/remote_trading_bot.log",
    "/home/ubuntu/kis-auto-trading/trading_bot.log",
    "/home/ubuntu/kis-auto-trading/bot.log",
]
_last_alert_sent: float = 0.0


def _is_market_hours() -> bool:
    """미국 동부시간 기준 장중 여부 (월~금 09:30~16:00)"""
    try:
        import pytz
        et  = pytz.timezone('US/Eastern')
        now = datetime.now(et)
        if now.weekday() >= 5:
            return False
        from datetime import time as dtime
        return dtime(9, 30) <= now.time() <= dtime(16, 0)
    except Exception:
        return False


def _get_log_mtime() -> float:
    """최근 갱신된 로그 파일의 mtime 반환"""
    latest = 0.0
    for path in _LOG_PATHS:
        try:
            mtime = os.path.getmtime(path)
            if mtime > latest:
                latest = mtime
        except Exception:
            pass
    return latest


def _heartbeat_loop() -> None:
    global _last_alert_sent
    logger.info("Heartbeat monitor started (silent limit: {}h)", _HEARTBEAT_SILENT_LIMIT // 3600)
    while True:
        try:
            if _is_market_hours():
                mtime = _get_log_mtime()
                if mtime > 0:
                    silent_secs = time.time() - mtime
                    if silent_secs > _HEARTBEAT_SILENT_LIMIT:
                        # 마지막 경보로부터 1시간 이상 지난 경우에만 재발송
                        if time.time() - _last_alert_sent > 3600:
                            silent_min = int(silent_secs // 60)
                            _send(
                                f"🚨 <b>봇 무활동 경보!</b>\n"
                                f"━━━━━━━━━━━━━━━━━━\n"
                                f"⏱ {silent_min}분째 로그 업데이트 없음\n"
                                f"💀 서비스가 다운됐을 수 있습니다!\n"
                                f"━━━━━━━━━━━━━━━━━━\n"
                                f"서버 접속 후 확인:\n"
                                f"<code>sudo systemctl status kis-trading</code>\n"
                                f"<code>sudo systemctl restart kis-trading</code>"
                            )
                            _last_alert_sent = time.time()
                            logger.warning("Heartbeat: bot silent for {}min — alert sent", silent_min)
        except Exception as e:
            logger.debug("Heartbeat error: {}", e)
        time.sleep(_HEARTBEAT_CHECK_INTERVAL)


if __name__ == "__main__":
    print("TelegramCommander 직접 실행 모드")
    _polling_loop()
