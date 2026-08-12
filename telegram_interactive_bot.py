"""
Telegram Interactive Remote Control Bot (v11.1.0 One-Click Interactive Buttons)
=================================================================================
Provides bi-directional remote control over the trading orchestrator via Telegram.
Supports interactive inline keyboard buttons for 100% one-click controls!
Commands & Buttons supported:
- /status or [📊 계좌 상태 조회]  : View real-time balance & positions
- /pause  or [⏸️ 매매 일시정지]  : Pause new entry screening loop
- /resume or [▶️ 매매 다시재개]  : Resume entry screening loop
- /close_all or [🚨 보유 종목 전량 긴급 청산] : Liquidate all active positions
- /help   or [도움말]            : Display One-Click Interactive Control Remote
"""

import threading
import time
import requests
from loguru import logger
import config

_is_bot_paused = False

def is_trading_paused() -> bool:
    return _is_bot_paused

class TelegramInteractiveBot:
    """Bi-directional Telegram Control Daemon with One-Click Interactive Buttons"""

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

    def _answer_callback(self, callback_query_id: str, text: str):
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/answerCallbackQuery"
            payload = {"callback_query_id": callback_query_id, "text": text}
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            logger.debug("Answer callback error: {}", e)

    def _send_one_click_menu(self):
        """Sends clean HTML menu with 100% one-click interactive buttons"""
        menu_text = (
            "🤖 <b>[v11.1 Ultra Quant 원스톱 리모컨]</b>\n"
            "원하시는 제어 버튼을 터치하여 바로 매매를 제어하세요!\n\n"
            "🌐 <b>웹 대시보드 주소</b>:\nhttp://141.148.172.12:8080"
        )
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "📊 계좌 상태 및 잔고 조회", "callback_data": "cmd_status"},
                    {"text": "🌐 실시간 웹 대시보드", "url": "http://141.148.172.12:8080"}
                ],
                [
                    {"text": "⏸️ 매매 일시정지", "callback_data": "cmd_pause"},
                    {"text": "▶️ 매매 다시재개", "callback_data": "cmd_resume"}
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

    def _handle_status(self):
        try:
            if not self.orchestrator:
                self._send_reply("ℹ️ 오케스트레이터가 초기화 대기 중입니다.")
                return

            bp = self.orchestrator.trader.get_buying_power()
            total_eq = self.orchestrator.trader.get_total_equity()
            positions = self.orchestrator.strategy.positions

            msg = (
                f"📊 <b>[실시간 계좌 & 포지션 리포트]</b>\n"
                f"• 총 자산: <b>${total_eq:,.2f}</b>\n"
                f"• 주문 가능 현금: <b>${bp:,.2f}</b>\n"
                f"• 매매 상태: {'⏸️ 일시정지' if _is_bot_paused else '🟢 정상 가동 중'}\n"
                f"• 보유 포지션 수: <b>{len(positions)}개</b>\n\n"
                f"🌐 <b>실시간 웹 대시보드</b>: http://141.148.172.12:8080\n\n"
            )

            if positions:
                msg += "<b>[현재 보유 포지션 목록]</b>\n"
                for sym, pos in positions.items():
                    curr_p = self.orchestrator.trader.get_price(sym)
                    if curr_p <= 0:
                        curr_p = pos.entry_price
                    pnl_p = ((curr_p - pos.entry_price) / pos.entry_price) * 100.0 if pos.entry_price > 0 else 0
                    sign = "🟢" if pnl_p >= 0 else "🔴"
                    msg += f"{sign} <b>{sym}</b>: {pos.quantity}주 | 평단가: ${pos.entry_price:.2f} | 현재가: ${curr_p:.2f} ({pnl_p:+.2f}%)\n"
            else:
                msg += "ℹ️ 현재 보유 중인 포지션이 없습니다.\n"

            reply_markup = {
                "inline_keyboard": [
                    [
                        {"text": "🔄 새로고침", "callback_data": "cmd_status"},
                        {"text": "🌐 대시보드 열기", "url": "http://141.148.172.12:8080"}
                    ]
                ]
            }
            self._send_reply(msg, reply_markup=reply_markup)

        except Exception as e:
            logger.error("Failed to fetch status for Telegram reply: {}", e)
            self._send_reply(f"⚠️ 상태 조회 중 오류 발생: {e}")

    def _handle_close_all(self):
        try:
            if not self.orchestrator:
                self._send_reply("ℹ️ 오케스트레이터가 초기화 대기 중입니다.")
                return

            positions = list(self.orchestrator.strategy.positions.items())
            if not positions:
                self._send_reply("ℹ️ 현재 청산할 포지션이 없습니다.")
                return

            self._send_reply(f"🚨 <b>[긴급 청산]</b> 보유 중인 {len(positions)}개 종목 전량 시장가 청산을 시작합니다...")
            sold_count = 0
            for sym, pos in positions:
                try:
                    price = self.orchestrator.trader.get_price(sym)
                    self.orchestrator.phase_5_execute_trade(sym, "SELL", pos.quantity, price, "TELEGRAM_EMERGENCY_CLOSE_ALL")
                    self.orchestrator.strategy.remove_position(sym)
                    sold_count += 1
                except Exception as se:
                    logger.error("Failed emergency sell for {}: {}", sym, se)

            self._send_reply(f"✅ <b>[긴급 청산 완료]</b> 총 {sold_count}개 종목 전량 청산 완료되었습니다.")
        except Exception as e:
            logger.error("Failed close_all for Telegram reply: {}", e)
            self._send_reply(f"⚠️ 긴급 청산 처리 중 오류 발생: {e}")
