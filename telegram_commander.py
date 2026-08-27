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
    if not _TOKEN or not _CHAT_ID or not text:
        return
    try:
        # 텔레그램 4096자 길이 초과 에러 방지용 자동 청킹(Chunking)
        if len(text) > 4000:
            chunks = [text[i:i+3800] for i in range(0, len(text), 3800)]
            for idx, chunk in enumerate(chunks):
                markup = reply_markup if idx == len(chunks) - 1 else None
                payload = {"chat_id": _CHAT_ID, "text": chunk, "parse_mode": "HTML"}
                if markup: payload["reply_markup"] = markup
                requests.post(
                    f"https://api.telegram.org/bot{_TOKEN}/sendMessage",
                    json=payload,
                    timeout=10,
                )
        else:
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
    except Exception as err:
        logger.warning("⚠️ [telegram_commander.py] Fallback triggered: {}", err)
    return []


# ─────────────────────────────────────────────
# 명령어 핸들러
# ─────────────────────────────────────────────

def _handle_status() -> str:
    lines = ["🤖 <b>스윙봇 실시간 모니터링</b>"]
    import pytz
    now_kst = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')
    now_edt = datetime.now(pytz.timezone('US/Eastern')).strftime('%H:%M:%S EDT')
    lines.append(f"⏰ <code>{now_kst} ({now_edt})</code>")
    
    # 1. 일시정지 상태 표시
    if os.path.exists("/tmp/kis_trading_paused"):
        lines.append("🔴 <b>매수 일시정지 상태</b> (/재개 로 활성화)")
    else:
        lines.append("✅ 정상 작동 중 (매수/청산 감시 활성화)")
        
    # 2. 오케스트레이터의 리스크 / 매크로 / 데이터 Fail-Safe 락다운 상태 조회
    try:
        from orchestrator import get_orchestrator
        orch = get_orchestrator()
        if orch:
            risk_lvl = orch.state.global_risk_level
            exp_pct = orch.state.max_exposure_pct
            regime = orch.state.current_regime
            univ_len = len(orch.state.target_universe)
            failed_mods = orch.state.modules_failed
            
            risk_emoji = "✅" if risk_lvl == "NORMAL" else "⚠️" if risk_lvl == "CAUTIOUS" else "🚨"
            lines.append(f"{risk_emoji} 리스크 레벨: <b>{risk_lvl}</b> (베팅비중 한도: {exp_pct:.0%})")
            lines.append(f"🌀 시장 감지 레짐: <b>{regime}</b>")
            
            # Fail-Safe 락다운 탐지 로직
            # 리스크 레벨이 RISK_OFF이고 비중이 최저 수준이거나 스크리너가 동결되었거나 모듈 실패가 존재할 경우
            if risk_lvl == "RISK_OFF" or failed_mods > 0 or univ_len == 0:
                lines.append("\n⚠️ <b>[Fail-Safe 락다운 분석]</b>")
                if univ_len == 0:
                    lines.append("• ❌ <b>스크리너 작동 장애 (진입 완전 동결)</b>\n  -> 데이터가 막혔거나 스크리너 로직 예외 발생!")
                if failed_mods > 0:
                    lines.append(f"• ❌ <b>일부 핵심 리스크 모듈 로드 실패 ({failed_mods}개)</b>\n  -> 무단 바이패스 방지를 위한 락다운 강제 활성화")
                if exp_pct <= 0.2:
                    lines.append("• ❌ <b>매크로/뉴스 크리티컬 리스크 감지 또는 데이터 결손</b>\n  -> 안전 확보를 위한 강제 비중 보수적 하향")
            else:
                lines.append(f"🎯 실시간 탐색 유니버스: <b>{univ_len}개 종목</b>")
        else:
            lines.append("⚠️ 오케스트레이터 인스턴스 미로딩 (기동 대기 중)")
    except Exception as e:
        lines.append(f"⚠️ 오케스트레이터 연동 오류: {e}")

    lines.append("━" * 18)
    
    # 3. 계좌 구매력 및 총 자산 요약
    try:
        from trader import get_trader
        trader = get_trader()
        bp = trader.get_buying_power()
        positions = trader.get_positions()
        total_val = bp + sum(getattr(p, 'market_value', 0) for p in positions)
        lines.append(f"💵 계좌 구매력: <b>${bp:,.2f}</b>")
        lines.append(f"📦 보유 포지션: <b>{len(positions)}개</b>")
        lines.append(f"💼 추정 총 자산: <b>${total_val:,.2f}</b>")
    except Exception as e:
        lines.append(f"⚠️ 계좌 잔고 조회 실패: {e}")
        
    lines.append("━" * 18)
    lines.append("🌐 <b>실시간 웹 대시보드</b>: http://141.148.172.12:8080")
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


def _handle_chart_30():
    _handle_chart(30)
    return None


def _handle_chart_90():
    _handle_chart(90)
    return None


def _handle_chart_180():
    _handle_chart(180)
    return None


def _handle_chart_365():
    _handle_chart(365)
    return None


def _handle_chart_all():
    _handle_chart(0)
    return None


def _handle_theme() -> str:
    """테마 레이더 탑픽 종목 조회"""
    try:
        from theme_radar_adapter import ThemeRadarAdapter
        adapter = ThemeRadarAdapter()
        recs = adapter.get_recommendations()
        if not recs:
            return "📭 현재 활성화된 테마 레이더 TRUE_SIGNAL 추천주가 없습니다."
        lines = ["🔥 <b>테마 레이더 100점 수식 검증 추천주</b>"]
        lines.append("━" * 18)
        for sym, data in list(recs.items())[:6]:
            pick = data.get("pick_type", "LEADER")
            theme = data.get("theme_name", "미상")
            tp = data.get("target_price", 0)
            sl = data.get("stop_loss", 0)
            lines.append(
                f"• <b>{sym:5s}</b> [{pick}] — {theme}\n"
                f"  🎯 목표가: ${tp:.2f} | 🛑 손절가: ${sl:.2f}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ 테마 추천 조회 실패: {e}"


def _handle_screener() -> str:
    """스크리너 실시간 포착 후보 종목 조회 (오케스트레이터 타겟 유니버스 연동)"""
    try:
        from orchestrator import get_orchestrator
        orch = get_orchestrator()
        cands = []
        if orch and hasattr(orch, 'state') and orch.state and orch.state.target_universe:
            cands = list(orch.state.target_universe)
            
        if not cands:
            from theme_radar_adapter import ThemeRadarAdapter
            recs = ThemeRadarAdapter().get_recommendations()
            cands = list(recs.keys())
            
        if not cands:
            return "📭 현재 스크리너 포착 조건에 부합하는 종목이 없습니다."
            
        lines = ["🎯 <b>실시간 퀀트 스크리너 포착 종목</b>"]
        lines.append("━" * 18)
        for sym in cands[:6]:
            lines.append(f"• <b>{sym:5s}</b> (모멘텀 돌파 수급 포착)")
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ 스크리너 조회 실패: {e}"


def _handle_regime() -> str:
    """실시간 시장 국면 레짐 분석 조회 (오케스트레이터 메모리 연동)"""
    try:
        from orchestrator import get_orchestrator
        orch = get_orchestrator()
        
        regime = "BULL_NORMAL"
        risk_lvl = "NORMAL"
        exp_pct = 1.0
        
        if orch and hasattr(orch, 'state') and orch.state:
            regime = getattr(orch.state, 'current_regime', 'BULL_NORMAL')
            risk_lvl = getattr(orch.state, 'global_risk_level', 'NORMAL')
            exp_pct = getattr(orch.state, 'max_exposure_pct', 1.0)
            
        risk_emoji = "🟢" if risk_lvl == "NORMAL" else "⚠️" if risk_lvl == "CAUTIOUS" else "🚨"
        
        lines = ["🌐 <b>실시간 시장 국면(Market Regime) 퀀트 분석</b>"]
        lines.append("━" * 18)
        lines.append(f"🌀 현재 감지 레짐: <b>{regime}</b>")
        lines.append(f"{risk_emoji} 매크로 리스크 상태: <b>{risk_lvl}</b>")
        lines.append(f"📊 최대 자산 베팅 한도: <b>{exp_pct:.0%}</b>")
        lines.append("━" * 18)
        if "BULL" in regime:
            lines.append("💡 <b>상승장 알파 전략</b>: 주도주 35% 집중 투자 & +9% 분할익절 가동 중")
        elif "BEAR" in regime:
            lines.append("💡 <b>하락장 방어 전략</b>: 현금 비중 확대 & 헤징 ETF 감시 가동 중")
        else:
            lines.append("💡 <b>횡보장 퀀트 전략</b>: 변동성 박스권 리스크 타이트 제어 중")
            
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ 레짐 분석 조회 실패: {e}"


def _handle_risk() -> str:
    """리스크 & 서킷브레이커 상태 조회"""
    try:
        from drawdown_controller import DrawdownController
        dc = DrawdownController()
        is_halted = dc.is_halted()
        halt_emoji = "🔴 서킷브레이커 발동 중" if is_halted else "🟢 서킷브레이커 정상 (매수 가능)"
        lines = ["🛡️ <b>리스크 & 서킷브레이커 상태</b>"]
        lines.append("━" * 18)
        lines.append(f"상태: <b>{halt_emoji}</b>")
        lines.append(f"주간 손실 한도: <b>-15.0%</b>")
        lines.append(f"최대 낙폭 한도: <b>-25.0%</b>")
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ 리스크 상태 조회 실패: {e}"


def _handle_weekly_pnl() -> str:
    """최근 7일 누적 성과 조회"""
    try:
        from database import get_database
        from datetime import timedelta, datetime
        db = get_database()
        end_d = datetime.now().date()
        start_d = end_d - timedelta(days=7)
        trades = db.get_trades_range(start_d, end_d)
        sells = [t for t in (trades or []) if t.side == "SELL"]
        if not sells:
            return "📭 최근 7일간 청산(SELL) 완료된 매매가 없습니다."
        total_pnl = sum(t.pnl for t in sells)
        wins = sum(1 for t in sells if t.pnl > 0)
        wr = (wins / len(sells) * 100) if sells else 0.0
        lines = [f"📅 <b>최근 7일 누적 매매 성과</b>"]
        lines.append("━" * 18)
        lines.append(f"총 청산 건수: <b>{len(sells)}건</b> ({wins}승 / {len(sells)-wins}패)")
        lines.append(f"실시간 승률: <b>{wr:.1f}%</b>")
        lines.append(f"7일 순손익: <b>${total_pnl:+,.2f}</b>")
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ 주간 성과 조회 실패: {e}"


def _handle_monthly_pnl() -> str:
    """최근 30일(월간) 누적 성과 조회"""
    try:
        from database import get_database
        from datetime import timedelta, datetime
        db = get_database()
        end_d = datetime.now().date()
        start_d = end_d - timedelta(days=30)
        trades = db.get_trades_range(start_d, end_d)
        sells = [t for t in (trades or []) if t.side == "SELL"]
        if not sells:
            return "📭 최근 30일간 청산(SELL) 완료된 매매가 없습니다."
        total_pnl = sum(t.pnl for t in sells)
        wins = sum(1 for t in sells if t.pnl > 0)
        wr = (wins / len(sells) * 100) if sells else 0.0
        lines = [f"📅 <b>최근 30일(월간) 누적 매매 성과</b>"]
        lines.append("━" * 18)
        lines.append(f"총 청산 건수: <b>{len(sells)}건</b> ({wins}승 / {len(sells)-wins}패)")
        lines.append(f"월간 승률: <b>{wr:.1f}%</b>")
        lines.append(f"30일 순손익: <b>${total_pnl:+,.2f}</b>")
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ 월간 성과 조회 실패: {e}"


def _handle_alltime_pnl() -> str:
    """봇 가동 전체 누적 성과 조회"""
    try:
        from database import get_database
        from datetime import date
        db = get_database()
        start_d = date(2020, 1, 1)
        end_d = date(2030, 12, 31)
        trades = db.get_trades_range(start_d, end_d)
        sells = [t for t in (trades or []) if t.side == "SELL"]
        if not sells:
            return "📭 아직 전체 누적 매매 청산 기록이 없습니다."
        total_pnl = sum(t.pnl for t in sells)
        wins = sum(1 for t in sells if t.pnl > 0)
        wr = (wins / len(sells) * 100) if sells else 0.0
        lines = ["🏆 <b>AI 스윙 봇 전체 누적 매매 성과 (All-Time)</b>"]
        lines.append("━" * 18)
        lines.append(f"총 누적 거래: <b>{len(sells)}건</b> ({wins}승 / {len(sells)-wins}패)")
        lines.append(f"전체 통산 승률: <b>{wr:.1f}%</b>")
        lines.append(f"통산 누적 순손익: <b>${total_pnl:+,.2f}</b>")
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ 전체 성과 조회 실패: {e}"


def _handle_help() -> tuple:
    paused = "🔴 일시정지 중" if os.path.exists("/tmp/kis_trading_paused") else "✅ 정상 가동"
    text = (
        f"📋 <b>AI 스윙 봇 인터랙티브 제어판</b> [{paused}]\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "원하시는 버튼을 터치하시면 실시간 상태, 성과, 추천주, 리스크 제어가 즉시 실행됩니다.\n\n"
        "🌐 <b>실시간 웹 대시보드</b>:\nhttp://141.148.172.12:8080"
    )
    markup = {
        "inline_keyboard": [
            [
                {"text": "🌐 실시간 웹 대시보드 열기", "url": "http://141.148.172.12:8080"}
            ],
            [
                {"text": "📊 봇 상태 요약", "callback_data": "/status"},
                {"text": "📈 보유 포지션", "callback_data": "/포지션"}
            ],
            [
                {"text": "💰 오늘 실현손익", "callback_data": "/수익"},
                {"text": "📅 7일 누적성과", "callback_data": "/주간수익"}
            ],
            [
                {"text": "📅 30일 월간성과", "callback_data": "/월간수익"},
                {"text": "🏆 전체 누적성과", "callback_data": "/전체수익"}
            ],
            [
                {"text": "🔥 테마 1등주", "callback_data": "/테마"},
                {"text": "🎯 스크리너 픽", "callback_data": "/스크리너"}
            ],
            [
                {"text": "🌐 시장 레짐", "callback_data": "/레짐"},
                {"text": "🛡️ 리스크 현황", "callback_data": "/리스크"}
            ],
            [
                {"text": "📊 30일 차트", "callback_data": "/차트30"},
                {"text": "📊 90일 차트", "callback_data": "/차트90"}
            ],
            [
                {"text": "⏸️ 매수 일시정지", "callback_data": "/일시정지"},
                {"text": "▶️ 매수 재개", "callback_data": "/재개"}
            ],
            [
                {"text": "🚨 보유 종목 전량 긴급 청산", "callback_data": "/전량청산"}
            ]
        ]
    }
    return text, markup


def _handle_close_all() -> str:
    try:
        from orchestrator import get_orchestrator
        orch = get_orchestrator()
        if not orch:
            return "⚠️ 오케스트레이터 미초기화 상태입니다."

        positions = list(orch.strategy.positions.items())
        if not positions:
            return "📭 현재 청산할 보유 포지션이 없습니다."

        sold_cnt = 0
        for sym, pos in positions:
            try:
                price = orch.trader.get_price(sym)
                orch.phase_5_execute_trade(sym, "SELL", pos.quantity, price, "TELEGRAM_EMERGENCY_CLOSE_ALL")
                orch.strategy.remove_position(sym)
                sold_cnt += 1
            except Exception as se:
                logger.error("Emergency sell failed for {}: {}", sym, se)

        return f"🚨 <b>[보유 종목 긴급 전량 청산 완료]</b> 총 {sold_cnt}개 종목 청산 완료되었습니다."
    except Exception as e:
        return f"⚠️ 긴급 청산 중 오류 발생: {e}"


_COMMANDS = {
    "/status":   _handle_status,
    "/상태":     _handle_status,
    "/잔고":     _handle_status,
    "/포지션":   _handle_positions,
    "/수익":     _handle_pnl,
    "/주간수익": _handle_weekly_pnl,
    "/월간수익": _handle_monthly_pnl,
    "/전체수익": _handle_alltime_pnl,
    "/테마":     _handle_theme,
    "/스크리너": _handle_screener,
    "/레짐":     _handle_regime,
    "/리스크":   _handle_risk,
    "/차트":     _handle_chart_90,
    "/차트30":   _handle_chart_30,
    "/차트90":   _handle_chart_90,
    "/차트180":  _handle_chart_180,
    "/차트365":  _handle_chart_365,
    "/차트전체": _handle_chart_all,
    "/차트0":    _handle_chart_all,
    "/chart":    _handle_chart_90,
    "/chart30":  _handle_chart_30,
    "/chart90":  _handle_chart_90,
    "/chart180": _handle_chart_180,
    "/chart365": _handle_chart_365,
    "/chartall": _handle_chart_all,
    "/chart0":   _handle_chart_all,
    "/일시정지": _handle_pause,
    "/pause":    _handle_pause,
    "/재개":     _handle_resume,
    "/resume":   _handle_resume,
    "/전량청산": _handle_close_all,
    "/close_all": _handle_close_all,
    "/도움말":   _handle_help,
    "/help":     _handle_help,
    "/start":    _handle_help,
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
                        except Exception as err:
                            logger.warning("⚠️ [telegram_commander.py] Fallback triggered: {}", err)

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
    "/home/ubuntu/kis-auto-trading/logs/trading_bot.log",
    "/home/ubuntu/kis-auto-trading/remote_trading_bot.log",
    "/home/ubuntu/kis-auto-trading/trading_bot.log",
    "/home/ubuntu/kis-auto-trading/bot.log",
    "logs/trading_bot.log",
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
        except Exception as err:
            logger.warning("⚠️ [telegram_commander.py] Fallback triggered: {}", err)
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
