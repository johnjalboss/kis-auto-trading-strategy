"""
Notifier Module - Telegram Alerts
==================================
Real-time notifications for trades, alerts, and daily reports.
"""

import asyncio
import threading
from datetime import datetime
from typing import Optional
from dataclasses import dataclass
from loguru import logger
import requests
import json

try:
    import telegram
    from telegram import Bot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("python-telegram-bot not installed")

import config


# ============================================================
# 매매 사유 한국어 번역기
# ============================================================
_REASON_MAP = {
    # 진입 신호
    "breakout": "저항선 돌파",
    "momentum": "강한 모멘텀",
    "squeeze": "볼린저 밴드 스퀴즈 해제",
    "volume surge": "거래량 급증",
    "volume": "비정상 거래량 감지",
    "trend": "상승 추세 진입",
    "composite signal": "복합 기술 신호 발생",
    "entry signal": "매수 신호",
    "bullish": "강세 신호",
    "rsi oversold": "RSI 과매도 구간 진입",
    "rsi": "RSI 신호",
    "macd": "MACD 골든크로스",
    "golden cross": "골든크로스 (단기선이 장기선 상향 돌파)",
    "moving average": "이동평균선 돌파",
    "52w high": "52주 신고가 근접",
    "gap up": "갭 상승 출발",
    # 청산 신호
    "take profit": "목표 수익률 달성 — 이익 실현",
    "stop loss": "손절 기준 도달 — 손절 매도",
    "trailing stop": "트레일링 스탑 발동 — 이익 보호",
    "time exit": "최대 보유 기간 초과 — 기간 청산",
    "max hold": "최대 보유 기간 초과 — 기간 청산",
    "bearish": "약세 신호 발생",
    "dead cross": "데드크로스 (단기선이 장기선 하향 이탈)",
    "rsi overbought": "RSI 과매수 구간 — 고점 매도",
    "sell signal": "매도 신호",
    "partial": "부분 이익 실현",
    "regime change": "시장 국면 전환 — 포지션 정리",
    "risk off": "리스크 오프 국면 진입 — 방어 매도",
    "drawdown": "최대 낙폭 초과 — 손실 제한",
    "upgrade": "더 우수한 종목으로 교체",
    "exposure": "전체 노출 비중 초과 — 비중 축소",
    "macro": "거시경제 위험 신호 감지",
    "vix": "VIX 급등 — 시장 변동성 경보",
    "emergency": "긴급 리스크 감지",
    "market closed": "장 마감",
    "sector": "섹터 중복 제한",
    "cooldown": "쿨다운 기간 (동일 종목 재진입 대기)",
}

def _translate_reason(reason: str) -> str:
    """매매 사유 문자열을 정밀하고 친절한 한국어 상세 설명으로 변환."""
    if not reason:
        return ""
    
    r_lower = reason.lower()

    # 🔄 UPGRADE / ROTATION (우수 종목 교체)
    if "upgrade" in r_lower or "replaced" in r_lower:
        import re
        match = re.search(r'upgrade:\s*([A-Za-z0-9_]+)\((\d+)\)\s*->\s*([A-Za-z0-9_]+)\((\d+)\)', reason, re.IGNORECASE)
        if match:
            old_s, old_sc, new_s, new_sc = match.groups()
            gap = int(new_sc) - int(old_sc)
            return f"🔄 <b>우수 주도주 교체 매매</b>\n기존 보유주 <code>{old_s}</code>({old_sc}점)보다 모멘텀/수급 점수가 <b>+{gap}점</b> 더 높은 최정예 주도주 <code>{new_s}</code>({new_sc}점)를 포착하여 기존 포지션 전량 매도 후 교체 집행."
        return f"🔄 <b>우수 주도주 교체 매매</b>\n수익률 및 수급 점수가 더 높은 우수 주도주로 교과서적 수급 이동 교체 매매 집행. (원문: {reason})"

    # 🔒 PROFIT LOCKING STOP (이익 보존 손절선)
    if "profit_lock" in r_lower:
        return f"🔒 <b>이익 보존 손절선(Profit Lock) 발동</b>\n주가 최고 상승 후 이익 보호 바닥선에 도달하여 이미 확보한 수익을 안전하게 확정 청산. (상세: {reason})"

    # 🚨 GEMINI AI EMERGENCY EXIT (실시간 악재 AI 청산)
    if "gemini_ai" in r_lower or "catastrophic" in r_lower:
        return f"🚨 <b>Gemini AI 실시간 악재 0.1초 긴급 청산</b>\n파산/SEC조사/사임 등 대형 악재 감지로 즉시 손실 차단 매도. (상세: {reason})"

    # 💤 DEAD MONEY EXIT (횡보주 빠른 예수금 회수)
    if "dead_money" in r_lower:
        return f"💤 <b>횡보주 조기 회수 (Dead Money Exit)</b>\n3일간 주가 횡보로 주도주 교체를 위해 예수금을 빠르게 회수."

    # ⏱️ DYNAMIC TIME EXPIRED (보유 기간 만료)
    if "dynamic_time_expired" in r_lower or "max_hold" in r_lower:
        return f"⏱️ <b>보유 기간 만료 청산</b>\n최대 보유 기간 도달로 포지션 정리 및 리스크 관리."

    # 🛑 HARD STOP (손절선 도달)
    if "hard_stop" in r_lower or "stop_loss" in r_lower:
        return f"🛑 <b>손절선(Stop-Loss) 도달</b>\n원칙적 리스크 방어를 위한 손절 매도. (상세: {reason})"

    for eng, kor in _REASON_MAP.items():
        if eng in r_lower:
            return kor
    return reason


@dataclass
class TradeAlert:
    """Trade notification data"""
    action: str
    symbol: str
    quantity: int
    price: float
    pnl_pct: float = 0.0
    reason: str = ""


class TelegramNotifier:
    """
    Telegram notification service
    
    Sends real-time alerts for:
    - Trade entries/exits
    - Daily P&L reports
    - Risk warnings
    - System status
    """
    
    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token or getattr(config, 'TELEGRAM_BOT_TOKEN', '')
        self.chat_id = chat_id or getattr(config, 'TELEGRAM_CHAT_ID', '')
        self.discord_url = getattr(config, 'DISCORD_WEBHOOK_URL', '')
        self._bot = None
        self._enabled = False
        self._discord_enabled = bool(self.discord_url)
        
        self._init_bot()
    
    def _init_bot(self):
        """Initialize Telegram bot"""
        import os
        if not self.bot_token:
            self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN') or getattr(config, 'TELEGRAM_BOT_TOKEN', '')
        if not self.chat_id:
            self.chat_id = os.getenv('TELEGRAM_CHAT_ID') or getattr(config, 'TELEGRAM_CHAT_ID', '')
        if not self.discord_url:
            self.discord_url = os.getenv('DISCORD_WEBHOOK_URL') or getattr(config, 'DISCORD_WEBHOOK_URL', '')
            self._discord_enabled = bool(self.discord_url)

        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram NOT fully configured yet (missing token/chat_id). Direct HTML requests will retry dynamic load on send.")
            self._enabled = False
            return
        
        self._enabled = True
        
        if not TELEGRAM_AVAILABLE:
            logger.info("Telegram notifier initialized (direct requests fallback mode, python-telegram-bot not installed)")
            return
        
        try:
            self._bot = Bot(token=self.bot_token)
            logger.info("Telegram Bot API instance initialized successfully")
        except Exception as e:
            logger.warning("Telegram Bot object init failed (will use requests fallback): {}", e)
    
    def _send_sync(self, message: str) -> bool:
        """Send message synchronously to Telegram and/or Discord. Returns True if successful."""
        import os
        success = True
        # 발송 시점에 설정이 비어있는 경우 동적 갱신 시도
        if not self.bot_token or not self.chat_id or not self._enabled:
            self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN') or getattr(config, 'TELEGRAM_BOT_TOKEN', '')
            self.chat_id = os.getenv('TELEGRAM_CHAT_ID') or getattr(config, 'TELEGRAM_CHAT_ID', '')
            if self.bot_token and self.chat_id:
                self._enabled = True
                logger.info("Telegram notifier dynamically enabled on send (token loaded)")
                
        if not self.discord_url:
            self.discord_url = os.getenv('DISCORD_WEBHOOK_URL') or getattr(config, 'DISCORD_WEBHOOK_URL', '')
            self._discord_enabled = bool(self.discord_url)

        # Telegram
        if self._enabled and self.bot_token and self.chat_id:
            try:
                url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
                payload = {
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "HTML"
                }
                resp = requests.post(url, json=payload, timeout=10)
                if not resp.ok:
                    logger.error(f"Telegram API error: {resp.status_code} {resp.text}")
                    success = False
                else:
                    logger.info("Telegram message successfully sent via HTTP request.")
            except Exception as e:
                logger.error(f"Telegram send failed: {e}")
                success = False
                
        # Discord (Format stripped from HTML to Markdown)
        if self._discord_enabled and self.discord_url:
            try:
                # Strip simple HTML from telegram format for discord
                discord_msg = message.replace('<b>', '**').replace('</b>', '**').replace('<code>', '`').replace('</code>', '`')
                payload = {"content": discord_msg}
                resp = requests.post(self.discord_url, json=payload, timeout=3)
                if not resp.ok:
                    success = False
            except Exception as e:
                logger.error("Discord send failed: {}", e)
                success = False
        
        return success
    
    def send(self, message: str):
        """Send message in background thread"""
        import os
        if not self._enabled and not self._discord_enabled:
            # 동적 재로드를 위해 환경변수를 슬쩍 검사해보고 둘다 없으면 그제서야 스킵
            token = os.getenv('TELEGRAM_BOT_TOKEN') or getattr(config, 'TELEGRAM_BOT_TOKEN', '')
            chat = os.getenv('TELEGRAM_CHAT_ID') or getattr(config, 'TELEGRAM_CHAT_ID', '')
            discord = os.getenv('DISCORD_WEBHOOK_URL') or getattr(config, 'DISCORD_WEBHOOK_URL', '')
            if not token and not chat and not discord:
                logger.debug("Notifications completely unconfigured, skipping: {}", message[:50])
                return
        
        threading.Thread(target=self._send_sync, args=(message,), daemon=True).start()

    def _send_photo_sync(self, photo_path: str, caption: str) -> bool:
        """Send photo synchronously to Telegram. Returns True if successful."""
        import os
        success = True
        # 발송 시점에 설정이 비어있는 경우 동적 갱신 시도
        if not self.bot_token or not self.chat_id or not self._enabled:
            self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN') or getattr(config, 'TELEGRAM_BOT_TOKEN', '')
            self.chat_id = os.getenv('TELEGRAM_CHAT_ID') or getattr(config, 'TELEGRAM_CHAT_ID', '')
            if self.bot_token and self.chat_id:
                self._enabled = True
                logger.info("Telegram notifier dynamically enabled on send_photo (token loaded)")

        if not self.discord_url:
            self.discord_url = os.getenv('DISCORD_WEBHOOK_URL') or getattr(config, 'DISCORD_WEBHOOK_URL', '')
            self._discord_enabled = bool(self.discord_url)

        if self._enabled and self.bot_token and self.chat_id:
            try:
                url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
                with open(photo_path, 'rb') as f:
                    files = {"photo": f}
                    data = {
                        "chat_id": self.chat_id,
                        "caption": caption,
                        "parse_mode": "HTML"
                    }
                    resp = requests.post(url, data=data, files=files, timeout=30)
                    if not resp.ok:
                        logger.error(f"Telegram Photo API error: {resp.status_code} {resp.text}")
                        success = False
            except Exception as e:
                logger.error(f"Telegram send_photo failed: {e}")
                success = False
                
        # Optional: Discord webhook support for images (multipart form-data)
        if self._discord_enabled and self.discord_url:
            try:
                discord_caption = caption.replace('<b>', '**').replace('</b>', '**').replace('<code>', '`').replace('</code>', '`')
                with open(photo_path, 'rb') as f:
                    resp = requests.post(self.discord_url, 
                                  data={"payload_json": json.dumps({"content": discord_caption})},
                                  files={"file": f}, 
                                  timeout=10)
                    if not resp.ok:
                        success = False
            except Exception as e:
                logger.error("Discord send_photo failed: {}", e)
                success = False
                
        return success

    def send_photo(self, photo_path: str, caption: str = ""):
        """Send photo in background thread"""
        import os
        if not self._enabled and not self._discord_enabled:
            # 동적 재로드를 위해 환경변수를 슬쩍 검사해보고 둘다 없으면 그제서야 스킵
            token = os.getenv('TELEGRAM_BOT_TOKEN') or getattr(config, 'TELEGRAM_BOT_TOKEN', '')
            chat = os.getenv('TELEGRAM_CHAT_ID') or getattr(config, 'TELEGRAM_CHAT_ID', '')
            discord = os.getenv('DISCORD_WEBHOOK_URL') or getattr(config, 'DISCORD_WEBHOOK_URL', '')
            if not token and not chat and not discord:
                logger.debug("Notifications completely unconfigured, skipping photo send")
                return
        threading.Thread(target=self._send_photo_sync, args=(photo_path, caption), daemon=True).start()
        
    def send_sync(self, message: str) -> bool:
        """Send message synchronously and return success status"""
        return self._send_sync(message)
        
    def send_photo_sync(self, photo_path: str, caption: str = "") -> bool:
        """Send photo synchronously and return success status"""
        return self._send_photo_sync(photo_path, caption)

    # ==============================================
    # Compatibility with legacy notification.py
    # ==============================================
    def send_message(self, message: str):
        """Alias for compatibility with legacy notification.py"""
        self.send(message)

    def send_all(self, message: str) -> bool:
        """Alias for compatibility with legacy notification.py"""
        return self._send_sync(message)

    def alert_status(self, status: str, details: str):
        """Alias for compatibility with legacy notification.py"""
        self.system_status(status, details)

    def alert_emergency(self, severity: str, reason: str):
        """Alias for compatibility with legacy notification.py"""
        self.risk_warning(f"EMERGENCY {severity}: {reason}")

    def alert_daily_summary(self, pnl: float, pnl_pct: float, trades: int):
        """Alias for compatibility with legacy notification.py"""
        self.daily_report(pnl, pnl_pct, trades)
        
    # ==============================================
    # Trade Alerts
    # ==============================================
    
    def alert_trade(self, side: str, symbol: str, price: float, details: str = "", quantity: int = 0, pnl_pct: float = 0.0):
        """General trade alert fallback method"""
        if side.upper() == "BUY":
            self.trade_entry(symbol, quantity, price, details)
        else:
            self.trade_exit(symbol, quantity, price, pnl_pct, details)

    def trade_entry(self, symbol: str, quantity: int, price: float, reason: str = ""):
        """Notify trade entry"""
        # 매수 이유 한국어 변환
        reason_ko = _translate_reason(reason)
        qty_str = f" x {quantity}주" if quantity > 0 else ""
        msg = (
            f"🟢 <b>매수 체결</b>\n"
            f"<code>{symbol}</code>{qty_str}\n"
            f"가격: ${price:.2f}\n"
        )
        if reason_ko:
            safe = reason_ko.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            msg += f"사유: {safe}\n"
        msg += f"⏰ {datetime.now().strftime('%H:%M:%S')}"
        self.send(msg)
    
    def trade_exit(self, symbol: str, quantity: int, price: float, 
                   pnl_pct: float, reason: str = ""):
        """Notify trade exit"""
        emoji = "💰" if pnl_pct > 0 else "🔻"
        pnl_label = "수익" if pnl_pct > 0 else "손실"
        reason_ko = _translate_reason(reason)
        qty_str = f" x {quantity}주" if quantity > 0 else ""
        msg = (
            f"{emoji} <b>매도 체결</b>\n"
            f"<code>{symbol}</code>{qty_str}\n"
            f"가격: ${price:.2f}\n"
            f"{pnl_label}: {pnl_pct:+.1%}\n"
        )
        if reason_ko:
            safe = reason_ko.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            msg += f"사유: {safe}\n"
        msg += f"⏰ {datetime.now().strftime('%H:%M:%S')}"
        self.send(msg)
    
    def partial_exit(self, symbol: str, quantity: int, price: float, pnl_pct: float):
        """Notify partial profit taking"""
        msg = (
            f"✂️ <b>일부 매도 (이익 실현)</b>\n"
            f"<code>{symbol}</code> x {quantity}주\n"
            f"가격: ${price:.2f}\n"
            f"수익률: {pnl_pct:+.1%}\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')}"
        )
        self.send(msg)
    
    # ==============================================
    # Risk Alerts
    # ==============================================
    
    def daily_stop_triggered(self, loss_pct: float, threshold: float):
        """Alert when daily stop loss triggered"""
        msg = (
            f"🚨 <b>일일 손절 한도 도달!</b>\n"
            f"손실: {loss_pct:.1%} (한도: {threshold:.1%})\n"
            f"<b>오늘 매매 일시 중단</b>\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')}"
        )
        self.send(msg)
    
    def consecutive_loss(self, count: int, cooldown_mins: int):
        """Alert on consecutive losses"""
        msg = (
            f"⚠️ <b>연속 손실 {count}회</b>\n"
            f"{cooldown_mins}분 휴식 후 재개\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')}"
        )
        self.send(msg)
    
    def risk_warning(self, message: str):
        """General risk warning"""
        msg_ko = _translate_reason(message)
        msg = f"⚠️ <b>⚠️ 리스크 경고</b>\n{msg_ko or message}"
        self.send(msg)
    
    # ==============================================
    # Market Alerts
    # ==============================================
    
    def macro_update(self, regime: str, betting_ratio: float, triggers: list):
        """Daily macro regime update"""
        emoji = "🟢" if regime == "RISK_ON" else "🔴"
        msg = (
            f"{emoji} <b>MACRO UPDATE</b>\n"
            f"Regime: {regime}\n"
            f"Betting: {betting_ratio:.0%}\n"
        )
        if triggers:
            msg += f"Triggers: {', '.join(triggers)}\n"
        self.send(msg)
    
    def premarket_alert(self, symbol: str, gap_pct: float, volume_ratio: float):
        """Pre-market gap/volume alert"""
        msg = (
            f"📈 <b>PRE-MARKET ALERT</b>\n"
            f"<code>{symbol}</code>\n"
            f"Gap: {gap_pct:+.1%}\n"
            f"Volume: {volume_ratio:.1f}x avg\n"
        )
        self.send(msg)
    
    def targets_found(self, tickers: list, regime: str):
        """Daily target stocks found"""
        msg = (
            f"🎯 <b>TODAY'S TARGETS</b>\n"
            f"Regime: {regime}\n"
            f"Stocks: {', '.join(tickers)}\n"
            f"⏰ {datetime.now().strftime('%H:%M')}"
        )
        self.send(msg)
    
    # ==============================================
    # Reports
    # ==============================================
    
    def daily_report(self, date: str, trades: int, winners: int, 
                     gross_pnl: float, net_pnl: float, win_rate: float):
        """End of day report"""
        emoji = "📈" if net_pnl >= 0 else "📉"
        result = "수익" if net_pnl >= 0 else "손실"
        msg = (
            f"{emoji} <b>오늘의 매매 결과 - {date}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"총 거래: {trades}건 ({winners}승/{trades-winners}패)\n"
            f"승률: {win_rate:.0%}\n"
            f"총 {result}: ${gross_pnl:+,.2f}\n"
            f"순 {result}: ${net_pnl:+,.2f}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        self.send(msg)
    
    def system_status(self, status: str, details: str = ""):
        """System status update"""
        status_ko = {"ACTIVE": "가동 중", "STOPPED": "중단됨", "ERROR": "오류", "RESTARTED": "재시작됨"}.get(status.upper(), status)
        msg = f"🤖 <b>시스템: {status_ko}</b>"
        if details:
            msg += f"\n{details}"
        self.send(msg)
    
    def screening_result(self, mode: str, regime: str, tickers: list, 
                          scores: list = None):
        """스크리닝 결과 상세 알림"""
        msg = (
            f"🔍 <b>SCREENING RESULT</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Mode: {mode}\n"
            f"Regime: {regime}\n"
            f"Found: {len(tickers)} stocks\n"
        )
        if scores:
            msg += "\n"
            for s in scores[:5]:
                msg += (f"  <code>{s.symbol:6s}</code> "
                       f"Score: {s.total_score}/100 "
                       f"(M:{s.momentum_score} T:{s.technical_score})\n")
        elif tickers:
            msg += f"\nStocks: {', '.join(tickers[:10])}\n"
        
        msg += f"\n⏰ {datetime.now().strftime('%H:%M:%S')}"
        self.send(msg)
    
    def entry_attempt(self, symbol: str, action: str, reason: str, 
                       confidence: int = 0):
        """진입 시도 결과 알림 (성공/실패 모두)"""
        reason_ko = _translate_reason(reason)
        safe_reason = (reason_ko or reason).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        if action == "BUY":
            msg = (
                f"✅ <b>매수 신호 발생</b>\n"
                f"<code>{symbol}</code>\n"
                f"신뢰도: {confidence}/100\n"
                f"사유: {safe_reason}\n"
                f"⏰ {datetime.now().strftime('%H:%M:%S')}"
            )
        else:
            msg = (
                f"⏸ <b>매수 건너뜀</b>\n"
                f"<code>{symbol}</code>\n"
                f"사유: {safe_reason}\n"
                f"⏰ {datetime.now().strftime('%H:%M:%S')}"
            )
        self.send(msg)
    
    def no_targets(self, reason: str = ""):
        """타겟 없음 알림"""
        msg = f"📭 <b>NO TARGETS FOUND</b>"
        if reason:
            msg += f"\n{reason}"
        msg += f"\n⏰ {datetime.now().strftime('%H:%M:%S')}"
        self.send(msg)
    
    @property
    def enabled(self) -> bool:
        return self._enabled


# Global instance
_notifier = None

def get_notifier() -> TelegramNotifier:
    global _notifier
    if _notifier is None:
        _notifier = TelegramNotifier()
    return _notifier


if __name__ == "__main__":
    print("Testing Telegram Notifier...")
    notifier = TelegramNotifier()
    print(f"Enabled: {notifier.enabled}")
    
    if not notifier.enabled:
        print("\nTo enable, add to .env:")
        print("  TELEGRAM_BOT_TOKEN=your_bot_token")
        print("  TELEGRAM_CHAT_ID=your_chat_id")
