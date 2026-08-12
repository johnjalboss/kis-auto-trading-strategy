"""
Telegram Interactive Remote Control Bot (v11.3.1 Complete Robust Position & Remote Remote)
==========================================================================================
Provides bi-directional remote control over the trading orchestrator via Telegram.
Supports interactive inline keyboard buttons for 100% one-click controls!
"""

import threading
import time
import os
import requests
from loguru import logger
import config

_is_bot_paused = False

def is_trading_paused() -> bool:
    return _is_bot_paused

class TelegramInteractiveBot:
    """Bi-directional Telegram Control Daemon with Complete One-Click Interactive Buttons & Charts"""

    def __init__(self, orchestrator_ref=None):
        self.orchestrator = orchestrator_ref
        self.bot_token = getattr(config, 'TELEGRAM_BOT_TOKEN', '')
        self.chat_id = getattr(config, 'TELEGRAM_CHAT_ID', '')
        self.last_update_id = 0
        self._running = False

    def start(self):
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram token or chat_id missing. Interactive bot disabled.")
            return

        self._running = True
        t = threading.Thread(target=self._poll_loop, daemon=True)
        t.start()
        logger.info("🤖 TelegramInteractiveBot daemon started (One-Click Interactive Remote Active)")

    def _send_reply(self, text: str, reply_markup: dict = None):
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            if reply_markup:
                payload["reply_markup"] = reply_markup
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            logger.debug("Telegram reply error: {}", e)

    def _send_photo(self, photo_path: str, caption: str = ""):
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
            if os.path.exists(photo_path):
                with open(photo_path, "rb") as f:
                    files = {"photo": f}
                    data = {"chat_id": self.chat_id, "caption": caption, "parse_mode": "HTML"}
                    requests.post(url, data=data, files=files, timeout=15)
            else:
                self._send_reply(f"⚠️ 차트 파일을 찾을 수 없습니다: {photo_path}")
        except Exception as e:
            logger.debug("Telegram photo send error: {}", e)

    def _answer_callback(self, callback_query_id: str, text: str):
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/answerCallbackQuery"
            payload = {"callback_query_id": callback_query_id, "text": text}
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            logger.debug("Answer callback error: {}", e)

    def _send_one_click_menu(self):
        """전체 19개 원클릭 인터랙티브 제어판 메뉴 전송"""
        paused = "🔴 일시정지 중" if _is_bot_paused else "✅ 정상 가동"
        menu_text = (
            f"📋 <b>AI 스윙 봇 인터랙티브 제어판</b> [{paused}]\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "원하시는 버튼을 터치하시면 실시간 상태, 성과, 차트, 추천주,\n"
            "리스크 제어가 즉시 실행됩니다.\n\n"
            "🌐 <b>실시간 웹 대시보드 주소</b>:\nhttps://dee-merger-endorsed-sas.trycloudflare.com"
        )
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "🌐 실시간 웹 대시보드 열기", "url": "https://dee-merger-endorsed-sas.trycloudflare.com"}
                ],
                [
                    {"text": "📊 봇 상태 요약", "callback_data": "cmd_status"},
                    {"text": "📈 보유 포지션", "callback_data": "cmd_positions"}
                ],
                [
                    {"text": "💰 오늘 실현손익", "callback_data": "cmd_today_pnl"},
                    {"text": "📅 7일 누적성과", "callback_data": "cmd_weekly_pnl"}
                ],
                [
                    {"text": "📅 30일 월간성과", "callback_data": "cmd_monthly_pnl"},
                    {"text": "🏆 전체 누적성과", "callback_data": "cmd_total_pnl"}
                ],
                [
                    {"text": "🔥 테마 1등주", "callback_data": "cmd_theme"},
                    {"text": "🎯 스크리너 픽", "callback_data": "cmd_screener"}
                ],
                [
                    {"text": "🌐 시장 레짐", "callback_data": "cmd_regime"},
                    {"text": "🛡️ 리스크 현황", "callback_data": "cmd_risk"}
                ],
                [
                    {"text": "📊 30일 차트", "callback_data": "cmd_chart30"},
                    {"text": "📊 90일 차트", "callback_data": "cmd_chart90"}
                ],
                [
                    {"text": "📊 180일 차트", "callback_data": "cmd_chart180"},
                    {"text": "📊 1년 차트", "callback_data": "cmd_chart365"}
                ],
                [
                    {"text": "📊 전체 수익차트", "callback_data": "cmd_chart_all"}
                ],
                [
                    {"text": "⏸️ 매수 일시정지", "callback_data": "cmd_pause"},
                    {"text": "▶️ 매수 재개", "callback_data": "cmd_resume"}
                ],
                [
                    {"text": "🚨 보유 종목 전량 긴급 청산", "callback_data": "cmd_close_all"}
                ]
            ]
        }
        self._send_reply(menu_text, reply_markup=reply_markup)

    def _poll_loop(self):
        global _is_bot_paused
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"

        while self._running:
            try:
                params = {"offset": self.last_update_id + 1, "timeout": 10}
                resp = requests.get(url, params=params, timeout=15)
                if resp.ok:
                    data = resp.json()
                    if data.get("ok") and "result" in data:
                        for update in data["result"]:
                            self.last_update_id = update["update_id"]

                            # 1. Handle Callback Query (Button Clicks)
                            if "callback_query" in update:
                                cb = update["callback_query"]
                                cb_id = cb.get("id")
                                cb_data = cb.get("data", "")
                                sender_id = str(cb.get("from", {}).get("id", ""))

                                if sender_id != str(self.chat_id):
                                    continue

                                if cb_data == "cmd_status":
                                    self._answer_callback(cb_id, "📊 계좌 상태를 조회합니다.")
                                    self._handle_status()
                                elif cb_data == "cmd_positions":
                                    self._answer_callback(cb_id, "📈 보유 포지션을 조회합니다.")
                                    self._handle_positions()
                                elif cb_data == "cmd_today_pnl":
                                    self._answer_callback(cb_id, "💰 오늘 실현손익을 조회합니다.")
                                    self._handle_pnl("today")
                                elif cb_data == "cmd_weekly_pnl":
                                    self._answer_callback(cb_id, "📅 7일 누적성과를 조회합니다.")
                                    self._handle_pnl("weekly")
                                elif cb_data == "cmd_monthly_pnl":
                                    self._answer_callback(cb_id, "📅 30일 월간성과를 조회합니다.")
                                    self._handle_pnl("monthly")
                                elif cb_data == "cmd_total_pnl":
                                    self._answer_callback(cb_id, "🏆 전체 누적성과를 조회합니다.")
                                    self._handle_pnl("total")
                                elif cb_data == "cmd_theme":
                                    self._answer_callback(cb_id, "🔥 테마 1등주를 조회합니다.")
                                    self._handle_theme()
                                elif cb_data == "cmd_screener":
                                    self._answer_callback(cb_id, "🎯 스크리너 픽을 조회합니다.")
                                    self._handle_screener()
                                elif cb_data == "cmd_regime":
                                    self._answer_callback(cb_id, "🌐 시장 레짐을 조회합니다.")
                                    self._handle_regime()
                                elif cb_data == "cmd_risk":
                                    self._answer_callback(cb_id, "🛡️ 리스크 현황을 조회합니다.")
                                    self._handle_risk()
                                elif cb_data == "cmd_chart30":
                                    self._answer_callback(cb_id, "📊 30일 차트를 생성합니다.")
                                    self._handle_chart(30)
                                elif cb_data == "cmd_chart90":
                                    self._answer_callback(cb_id, "📊 90일 차트를 생성합니다.")
                                    self._handle_chart(90)
                                elif cb_data == "cmd_chart180":
                                    self._answer_callback(cb_id, "📊 180일 차트를 생성합니다.")
                                    self._handle_chart(180)
                                elif cb_data == "cmd_chart365":
                                    self._answer_callback(cb_id, "📊 1년 차트를 생성합니다.")
                                    self._handle_chart(365)
                                elif cb_data == "cmd_chart_all":
                                    self._answer_callback(cb_id, "📊 전체 수익차트를 생성합니다.")
                                    self._handle_chart(0)
                                elif cb_data == "cmd_pause":
                                    _is_bot_paused = True
                                    self._answer_callback(cb_id, "⏸️ 매매가 일시정지되었습니다.")
                                    self._send_reply("⏸️ <b>[원격 제어] 매매 일시 정지</b>\n새로운 매수 신호 탐색을 일시 중단합니다. (/resume 또는 버튼으로 다시 가동)")
                                elif cb_data == "cmd_resume":
                                    _is_bot_paused = False
                                    self._answer_callback(cb_id, "▶️ 매매가 재개되었습니다.")
                                    self._send_reply("▶️ <b>[원격 제어] 매매 재개</b>\n무인 자율 매매 탐색 루프를 재가동합니다.")
                                elif cb_data == "cmd_close_all":
                                    self._answer_callback(cb_id, "🚨 보유 종목 긴급 청산 실행!")
                                    self._handle_close_all()

                            # 2. Handle Text Commands
                            elif "message" in update:
                                msg = update["message"]
                                text = msg.get("text", "").strip()
                                sender_id = str(msg.get("chat", {}).get("id", ""))

                                if sender_id != str(self.chat_id):
                                    continue

                                cmd = text.lower().strip()

                                if cmd in ["/status", "/상태", "/잔고", "상태", "잔고"] or cmd.startswith("/status"):
                                    self._handle_status()
                                elif cmd in ["/포지션", "포지션", "/positions"]:
                                    self._handle_positions()
                                elif cmd in ["/수익", "수익", "/pnl"]:
                                    self._handle_pnl("today")
                                elif cmd in ["/차트30", "차트30"]:
                                    self._handle_chart(30)
                                elif cmd in ["/차트90", "차트90"]:
                                    self._handle_chart(90)
                                elif cmd in ["/pause", "/정지", "/일시정지", "일시정지", "정지"]:
                                    _is_bot_paused = True
                                    self._send_reply("⏸️ <b>[원격 제어] 매매 일시 정지</b>\n새로운 매수 신호 탐색을 일시 중단합니다. (/resume 또는 /재개 로 다시 가동)")
                                elif cmd in ["/resume", "/재개", "/시작", "재개", "시작"]:
                                    _is_bot_paused = False
                                    self._send_reply("▶️ <b>[원격 제어] 매매 재개</b>\n무인 자율 매매 탐색 루프를 재가동합니다.")
                                elif cmd in ["/close_all", "/전량청산", "/청산", "전량청산", "청산"]:
                                    self._handle_close_all()
                                elif cmd in ["/help", "/도움말", "/start", "도움말", "help"] or cmd.startswith("/start") or cmd.startswith("/help"):
                                    self._send_one_click_menu()

            except Exception as e:
                logger.debug("Telegram poll error: {}", e)

            time.sleep(3)

    # ───────────────────────────────────────────────
    # Helper Methods
    # ───────────────────────────────────────────────

    def _get_positions_dict(self):
        """안전하게 보유 포지션 dict를 반환.
        우선순위: 1) KIS 브로커 API (실시간) → 2) StrategyEngine 메모리 → 3) SQLite DB
        """

        class _PosDummy:
            """KIS PositionInfo / DB row 양쪽을 통일된 인터페이스로 감싸는 래퍼"""
            def __init__(self, qty, avg_p, curr_p=None):
                self.quantity = int(qty)
                self.avg_price = float(avg_p)
                self.entry_price = float(avg_p)      # alias
                self.current_price = float(curr_p) if curr_p else float(avg_p)

        # ── 1순위: KIS 브로커 API (항상 실시간) ──────────────────────────
        if self.orchestrator and hasattr(self.orchestrator, 'trader') and self.orchestrator.trader:
            try:
                k_pos = self.orchestrator.trader.get_positions()
                if k_pos:
                    result = {}
                    for p in k_pos:
                        avg_p = getattr(p, 'avg_price', getattr(p, 'entry_price', 0.0))
                        curr_p = getattr(p, 'current_price', avg_p)
                        result[p.symbol] = _PosDummy(p.quantity, avg_p, curr_p)
                    logger.debug("KIS API positions: {} symbols", len(result))
                    return result
            except Exception as ke:
                logger.warning("KIS get_positions() failed, falling back: {}", ke)

        # ── 2순위: StrategyEngine 인메모리 포지션 ─────────────────────────
        if self.orchestrator and hasattr(self.orchestrator, 'strategy') and self.orchestrator.strategy:
            strat = self.orchestrator.strategy
            mem = getattr(strat, '_positions', getattr(strat, 'positions', {}))
            if mem:
                result = {}
                for sym, pos in mem.items():
                    avg_p = getattr(pos, 'avg_price', getattr(pos, 'entry_price', 0.0))
                    curr_p = getattr(pos, 'current_price', avg_p)
                    qty = getattr(pos, 'quantity', getattr(pos, 'qty', 0))
                    result[sym] = _PosDummy(qty, avg_p, curr_p)
                logger.debug("Strategy memory positions: {} symbols", len(result))
                return result

        # ── 3순위: SQLite DB (마지막 수단, 오래된 데이터일 수 있음) ─────────
        try:
            import sqlite3
            db_path = "trades.db"
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute("SELECT symbol, quantity, avg_price FROM positions WHERE quantity > 0")
                rows = cur.fetchall()
                conn.close()
                if rows:
                    result = {row[0]: _PosDummy(row[1], row[2]) for row in rows}
                    logger.warning("Using stale DB positions ({} symbols) — KIS API unavailable", len(result))
                    return result
        except Exception as e:
            logger.debug("DB positions fallback error: {}", e)

        return {}

    # ───────────────────────────────────────────────
    # Handler Methods
    # ───────────────────────────────────────────────

    def _handle_status(self):
        """봇 상태 요약 조회 (실증 데이터 우선, 가짜 하드코딩 0%)"""
        try:
            bp = 0.0
            positions = self._get_positions_dict()

            # 1. KIS 브로커 실시간 주문가능 현금 조회
            if self.orchestrator and hasattr(self.orchestrator, 'trader') and self.orchestrator.trader:
                try:
                    bp = self.orchestrator.trader.get_buying_power()
                except Exception as e:
                    logger.debug("Status handler get_buying_power failed: {}", e)
            else:
                # Trader direct fallback
                try:
                    from trader import Trader
                    t = Trader()
                    bp = t.get_buying_power()
                except Exception:
                    bp = 0.0

            # Calculate total equity
            pos_val = 0.0
            for sym, pos in positions.items():
                entry_p = getattr(pos, 'entry_price', getattr(pos, 'avg_price', 0.0))
                price = entry_p
                if self.orchestrator and hasattr(self.orchestrator, 'trader'):
                    try:
                        lp = self.orchestrator.trader.get_price(sym)
                        if lp > 0: price = lp
                    except Exception: pass
                pos_val += (price * pos.quantity)
            
            total_eq = bp + pos_val

            msg = (
                f"📊 <b>[실시간 계좌 & 포지션 리포트]</b>\n"
                f"• 총 자산: <b>${total_eq:,.2f}</b>\n"
                f"• 주문 가능 현금: <b>${bp:,.2f}</b>\n"
                f"• 매매 상태: {'⏸️ 일시정지' if _is_bot_paused else '🟢 정상 가동 중'}\n"
                f"• 보유 포지션 수: <b>{len(positions)}개</b>\n\n"
                f"🌐 <b>실시간 웹 대시보드</b>: https://dee-merger-endorsed-sas.trycloudflare.com\n\n"
            )

            if positions:
                msg += "<b>[현재 보유 포지션 목록]</b>\n"
                for sym, pos in positions.items():
                    entry_p = getattr(pos, 'entry_price', getattr(pos, 'avg_price', 0.0))
                    curr_p = entry_p
                    if self.orchestrator and hasattr(self.orchestrator, 'trader'):
                        try:
                            lp = self.orchestrator.trader.get_price(sym)
                            if lp > 0: curr_p = lp
                        except Exception: pass

                    pnl_p = ((curr_p - entry_p) / entry_p) * 100.0 if entry_p > 0 else 0
                    sign = "🟢" if pnl_p >= 0 else "🔴"
                    msg += f"{sign} <b>{sym}</b>: {pos.quantity}주 | 평단가: ${entry_p:.2f} | 현재가: ${curr_p:.2f} ({pnl_p:+.2f}%)\n"
            else:
                msg += "ℹ️ 현재 보유 중인 포지션이 없습니다.\n"

            reply_markup = {
                "inline_keyboard": [
                    [
                        {"text": "🔄 새로고침", "callback_data": "cmd_status"},
                        {"text": "🌐 대시보드 열기", "url": "https://dee-merger-endorsed-sas.trycloudflare.com"}
                    ]
                ]
            }
            self._send_reply(msg, reply_markup=reply_markup)

        except Exception as e:
            logger.error("Failed to fetch status for Telegram reply: {}", e)
            self._send_reply(f"⚠️ 상태 조회 중 오류 발생: {e}")

    def _handle_positions(self):
        """보유 포지션 상세 조회 (P&L 포함)"""
        try:
            positions = self._get_positions_dict()
            if not positions:
                self._send_reply("📭 현재 보유 포지션이 없습니다.")
                return
            lines = [f"📈 <b>현재 보유 포지션 ({len(positions)}개)</b>", "━" * 18]
            for sym, pos in positions.items():
                entry_p = getattr(pos, 'entry_price', getattr(pos, 'avg_price', 0.0))
                curr_p = entry_p
                if self.orchestrator and hasattr(self.orchestrator, 'trader'):
                    try:
                        lp = self.orchestrator.trader.get_price(sym)
                        if lp > 0: curr_p = lp
                    except Exception: pass

                pnl_pct = ((curr_p - entry_p) / entry_p * 100) if entry_p > 0 else 0
                pnl_usd = (curr_p - entry_p) * pos.quantity
                sign = "🟢" if pnl_pct >= 0 else "🔴"
                lines.append(
                    f"{sign} <b>{sym}</b>: {pos.quantity}주\n"
                    f"  평단가: ${entry_p:.2f} | 현재가: ${curr_p:.2f}\n"
                    f"  손익: <b>${pnl_usd:+,.2f}</b> ({pnl_pct:+.2f}%)"
                )
            self._send_reply("\n".join(lines))
        except Exception as e:
            logger.error("Failed positions lookup: {}", e)
            self._send_reply(f"⚠️ 포지션 조회 실패: {e}")

    def _handle_pnl(self, period: str = "today"):
        """실현손익 조회 (period: today / weekly / monthly / total)"""
        try:
            from database import get_database
            from datetime import timedelta, datetime, date
            db = get_database()
            now = datetime.now()
            if period == "today":
                start_d = now.date()
                end_d = now.date()
                title = "💰 <b>오늘의 실현 손익</b>"
                empty_msg = "📭 오늘은 아직 청산(SELL) 완료된 매매가 없습니다."
            elif period == "weekly":
                end_d = now.date()
                start_d = end_d - timedelta(days=7)
                title = "📅 <b>최근 7일 누적 매매 성과</b>"
                empty_msg = "📭 최근 7일간 청산(SELL) 완료된 매매가 없습니다."
            elif period == "monthly":
                end_d = now.date()
                start_d = end_d - timedelta(days=30)
                title = "📅 <b>최근 30일(월간) 누적 매매 성과</b>"
                empty_msg = "📭 최근 30일간 청산(SELL) 완료된 매매가 없습니다."
            else:  # total
                start_d = date(2020, 1, 1)
                end_d = date(2030, 12, 31)
                title = "🏆 <b>AI 스윙 봇 전체 누적 매매 성과 (All-Time)</b>"
                empty_msg = "📭 아직 전체 누적 매매 청산 기록이 없습니다."
            trades = db.get_trades_range(start_d, end_d)
            sells = [t for t in (trades or []) if t.side == "SELL"]
            if not sells:
                self._send_reply(empty_msg)
                return
            total_pnl = sum(t.pnl for t in sells)
            wins = sum(1 for t in sells if t.pnl > 0)
            wr = (wins / len(sells) * 100) if sells else 0.0
            lines = [title, "━" * 18]
            lines.append(f"총 청산 건수: <b>{len(sells)}건</b> ({wins}승 / {len(sells)-wins}패)")
            lines.append(f"승률: <b>{wr:.1f}%</b>")
            lines.append(f"순손익: <b>${total_pnl:+,.2f}</b>")
            self._send_reply("\n".join(lines))
        except Exception as e:
            self._send_reply(f"⚠️ 손익 조회 실패: {e}")

    def _handle_theme(self):
        """테마 레이더 탑픽 종목 조회"""
        try:
            from theme_radar_adapter import ThemeRadarAdapter
            recs = ThemeRadarAdapter().get_recommendations()
            if not recs:
                self._send_reply("📭 현재 활성화된 테마 레이더 TRUE_SIGNAL 추천주가 없습니다.")
                return
            lines = ["🔥 <b>테마 레이더 100점 수식 검증 추천주</b>", "━" * 18]
            for sym, data in list(recs.items())[:6]:
                pick = data.get("pick_type", "LEADER")
                theme = data.get("theme_name", "미상")
                tp = data.get("target_price", 0)
                sl = data.get("stop_loss", 0)
                lines.append(
                    f"• <b>{sym:5s}</b> [{pick}] — {theme}\n"
                    f"  🎯 목표가: ${tp:.2f} | 🛑 손절가: ${sl:.2f}"
                )
            self._send_reply("\n".join(lines))
        except Exception as e:
            self._send_reply(f"⚠️ 테마 추천 조회 실패: {e}")

    def _handle_screener(self):
        """스크리너 실시간 포착 후보 종목 조회"""
        try:
            cands = []
            if self.orchestrator and hasattr(self.orchestrator, 'state') and self.orchestrator.state:
                if hasattr(self.orchestrator.state, 'target_universe') and self.orchestrator.state.target_universe:
                    cands = list(self.orchestrator.state.target_universe)
            if not cands:
                from theme_radar_adapter import ThemeRadarAdapter
                recs = ThemeRadarAdapter().get_recommendations()
                cands = list(recs.keys())
            if not cands:
                self._send_reply("📭 현재 스크리너 포착 조건에 부합하는 종목이 없습니다.")
                return
            lines = ["🎯 <b>실시간 퀀트 스크리너 포착 종목</b>", "━" * 18]
            for sym in cands[:8]:
                lines.append(f"• <b>{sym:5s}</b> (모멘텀 돌파 수급 포착)")
            self._send_reply("\n".join(lines))
        except Exception as e:
            self._send_reply(f"⚠️ 스크리너 조회 실패: {e}")

    def _handle_regime(self):
        """실시간 시장 국면 레짐 분석 조회"""
        try:
            regime = "BULL_NORMAL"
            risk_lvl = "NORMAL"
            exp_pct = 1.0
            if self.orchestrator and hasattr(self.orchestrator, 'state') and self.orchestrator.state:
                regime = getattr(self.orchestrator.state, 'current_regime', 'BULL_NORMAL')
                risk_lvl = getattr(self.orchestrator.state, 'global_risk_level', 'NORMAL')
                exp_pct = getattr(self.orchestrator.state, 'max_exposure_pct', 1.0)
            risk_emoji = "🟢" if risk_lvl == "NORMAL" else "⚠️" if risk_lvl == "CAUTIOUS" else "🚨"
            lines = ["🌐 <b>실시간 시장 국면(Market Regime) 퀀트 분석</b>", "━" * 18]
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
            self._send_reply("\n".join(lines))
        except Exception as e:
            self._send_reply(f"⚠️ 레짐 분석 조회 실패: {e}")

    def _handle_risk(self):
        """리스크 & 서킷브레이커 상태 조회"""
        try:
            from drawdown_controller import DrawdownController
            dc = DrawdownController()
            is_halted = dc.is_halted()
            halt_emoji = "🔴 서킷브레이커 발동 중" if is_halted else "🟢 서킷브레이커 정상 (매수 가능)"
            lines = ["🛡️ <b>리스크 & 서킷브레이커 상태</b>", "━" * 18]
            lines.append(f"상태: <b>{halt_emoji}</b>")
            lines.append("주간 손실 한도: <b>-15.0%</b>")
            lines.append("최대 낙폭 한도: <b>-25.0%</b>")
            self._send_reply("\n".join(lines))
        except Exception as e:
            self._send_reply(f"⚠️ 리스크 상태 조회 실패: {e}")

    def _handle_chart(self, days: int = 90):
        """수익 차트 생성 및 전송 (30/90/180/365일)"""
        try:
            from chart_generator import generate_daily_pnl_chart
            chart_path = generate_daily_pnl_chart(days=days)
            if chart_path and os.path.exists(chart_path):
                period_str = "전체 기간" if days <= 0 else f"{days}일"
                self._send_photo(chart_path, f"📊 <b>수익 차트 ({period_str})</b>")
            else:
                self._send_reply("⚠️ 차트 생성 실패: 거래 데이터가 없거나 오류가 발생했습니다.")
        except Exception as e:
            self._send_reply(f"⚠️ 차트 생성 중 오류 발생: {e}")

    def _handle_close_all(self):
        """보유 종목 전량 긴급 청산"""
        try:
            positions = self._get_positions_dict()
            if not positions:
                self._send_reply("ℹ️ 현재 청산할 포지션이 없습니다.")
                return

            self._send_reply(f"🚨 <b>[긴급 청산]</b> 보유 중인 {len(positions)}개 종목 전량 시장가 청산을 시작합니다...")
            sold_count = 0
            for sym, pos in list(positions.items()):
                try:
                    price = pos.entry_price
                    if self.orchestrator and hasattr(self.orchestrator, 'trader'):
                        lp = self.orchestrator.trader.get_price(sym)
                        if lp > 0: price = lp
                    if self.orchestrator:
                        self.orchestrator.phase_5_execute_trade(sym, "SELL", pos.quantity, price, "TELEGRAM_EMERGENCY_CLOSE_ALL")
                        if hasattr(self.orchestrator.strategy, 'remove_position'):
                            self.orchestrator.strategy.remove_position(sym)
                    sold_count += 1
                except Exception as se:
                    logger.error("Failed emergency sell for {}: {}", sym, se)

            self._send_reply(f"✅ <b>[긴급 청산 완료]</b> 총 {sold_count}개 종목 전량 청산 처리 완료되었습니다.")
        except Exception as e:
            logger.error("Failed close_all for Telegram reply: {}", e)
            self._send_reply(f"⚠️ 긴급 청산 처리 중 오류 발생: {e}")
