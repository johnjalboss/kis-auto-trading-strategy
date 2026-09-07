"""
Pre-Market Gap Sentinel (pre_market_gap_sentinel.py)
====================================================
Designed by World #1 Quant Systems Architecture.
Runs 30 minutes before US regular market open (22:00 KST / 09:00 EDT)
to detect violent pre-market opening gaps (>= +/-3.0%) across held positions
and key benchmark/growth leaders.

Data Timing & Precision:
- Reference Base: Previous regular trading session's official close (전일 정규장 종가)
- Live Comparison: Real-time extended hours 1-minute tick price (당일 프리마켓 실시간 체결가)
- Precision Guard: Timezone-aware date boundaries (US/Eastern) prevent multi-day skew.
"""

import os
import sqlite3
import pytz
import yfinance as yf
import pandas as pd
from datetime import datetime
from loguru import logger
import requests
import config

class PreMarketGapSentinel:
    """Detects pre-market opening gaps and alerts the trader with actionable quant guidance."""

    def __init__(self, db_path: str = None):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = db_path or os.path.join(script_dir, "trades.db")
        self.bot_token = getattr(config, 'TELEGRAM_BOT_TOKEN', '')
        self.chat_id = getattr(config, 'TELEGRAM_CHAT_ID', '')

    def get_held_symbols(self) -> list:
        """Fetch actual live positions strictly from Broker API, Database, and Strategy."""
        # 1. Live broker / Trader prioritized first
        try:
            from trader import get_trader
            tr = get_trader()
            pos_list = tr.get_positions()
            if pos_list:
                symbols = [p.symbol for p in pos_list if getattr(p, 'quantity', 0) > 0]
                if symbols:
                    return symbols
                return [] # Broker returned explicit 0 positions
        except Exception as _tr_err:
            logger.debug("Live trader get_positions skipped in sentinel: {}", _tr_err)

        # 2. Direct SQLite query on target trades.db with active quantity > 0
        try:
            if os.path.exists(self.db_path):
                conn = sqlite3.connect(self.db_path)
                cur = conn.cursor()
                cur.execute("SELECT symbol FROM positions WHERE quantity > 0")
                rows = cur.fetchall()
                conn.close()
                if rows:
                    return [r[0] for r in rows]
        except Exception as _sql_err:
            logger.debug("Direct SQL positions query skipped: {}", _sql_err)

        return []

    def get_dynamic_watchlist(self) -> list:
        """Dynamically builds watch candidates from:
        1. Key Sector/Market Benchmark ETFs (QQQ, SPY, SMH, IWM, DIA)
        2. High-Beta Market & AI Growth Leaders
        """
        candidates = ["QQQ", "SPY", "SMH", "IWM", "DIA"]
        growth_leaders = ["NVDA", "PLTR", "LLY", "VRT", "CRWD", "APP", "TSLA", "AMD", "META", "AAPL", "MSFT", "AMZN"]
        for sym in growth_leaders:
            if sym not in candidates:
                candidates.append(sym)

        return candidates

    def scan_gaps(self, threshold_pct: float = 3.0) -> dict:
        """Scan held positions and top universe stocks for pre-market gaps with prepost=True."""
        held = self.get_held_symbols()
        watchlist = self.get_dynamic_watchlist()
        all_symbols = list(dict.fromkeys(held + watchlist))

        gap_alerts = []
        held_status = []

        now_ny = datetime.now(pytz.timezone('US/Eastern'))
        today_ny = now_ny.date()

        for sym in all_symbols:
            try:
                t = yf.Ticker(sym)
                last_price = 0.0
                prev_close = 0.0
                prev_date_str = ""
                quote_time_str = ""

                # 1. Daily history for exact previous regular session close
                try:
                    df_daily = t.history(period="5d")
                    if df_daily is not None and not df_daily.empty:
                        # If the last bar is from today and market is already open
                        if df_daily.index[-1].date() == today_ny and (now_ny.hour > 9 or (now_ny.hour == 9 and now_ny.minute >= 30)):
                            prev_close = float(df_daily['Close'].iloc[-2])
                            prev_date_str = df_daily.index[-2].strftime('%m/%d')
                        else:
                            prev_close = float(df_daily['Close'].iloc[-1])
                            prev_date_str = df_daily.index[-1].strftime('%m/%d')
                except Exception as e_d:
                    logger.debug("Daily fetch error for {}: {}", sym, e_d)

                # 2. Try 1m intraday with prepost=True for true extended hours live quotes
                try:
                    df_intra = t.history(period="1d", interval="1m", prepost=True)
                    if df_intra is not None and not df_intra.empty:
                        last_price = float(df_intra['Close'].iloc[-1])
                        quote_time_str = df_intra.index[-1].strftime('%H:%M EDT')
                except Exception as e_i:
                    logger.debug("Intra fetch error for {}: {}", sym, e_i)

                # 3. Fallback to fast_info if needed
                if prev_close <= 0:
                    try:
                        fast = t.fast_info
                        prev_close = float(fast.get("previous_close", 0.0) or fast.get("regular_market_previous_close", 0.0) or 0.0)
                        prev_date_str = "전일"
                    except Exception:
                        pass

                if last_price <= 0:
                    last_price = prev_close
                    quote_time_str = "체결대기"

                if prev_close > 0 and last_price > 0:
                    gap_pct = ((last_price - prev_close) / prev_close) * 100.0
                    is_held = sym in held

                    info = {
                        "symbol": sym,
                        "is_held": is_held,
                        "last_price": last_price,
                        "prev_close": prev_close,
                        "prev_date": prev_date_str,
                        "quote_time": quote_time_str,
                        "gap_pct": gap_pct
                    }

                    if is_held:
                        held_status.append(info)

                    if abs(gap_pct) >= threshold_pct:
                        gap_alerts.append(info)
            except Exception as e:
                logger.debug("Pre-market scan error for {}: {}", sym, e)

        # Sort gap alerts by absolute gap size descending
        gap_alerts.sort(key=lambda x: abs(x["gap_pct"]), reverse=True)

        return {
            "gap_alerts": gap_alerts,
            "held_status": held_status,
            "scanned_count": len(all_symbols)
        }

    def generate_report(self) -> str:
        """Generates pre-market opening intelligence brief or holiday notice."""
        from scheduler import TradingScheduler
        sched = TradingScheduler()
        now_est = sched.now_est()
        today_ny_str = now_est.strftime("%Y-%m-%d")
        holiday_name = sched.get_holiday_name(today_ny_str)
        is_trading = sched.is_trading_day()

        now_dt = datetime.now()
        now_str = now_dt.strftime("%Y-%m-%d %H:%M")
        now_ny = now_est.strftime("%H:%M EDT")

        # 1. Holiday Briefing
        if holiday_name:
            lines = [
                f"🏖️ <b>[미국 증시 공휴일 휴장 안내]</b>",
                f"<i>{now_str} KST ({now_ny} 기준)</i>",
                "━━━━━━━━━━━━━━━━━━━",
                f"오늘은 미국 <b>{holiday_name}</b> 공휴일로 뉴욕 증시(NYSE / NASDAQ)가 <b>전면 휴장</b>합니다.\n",
                "• ☕ <b>장 운영 안내:</b> 프리마켓, 정규장, 애프터마켓 거래가 모두 진행되지 않습니다.",
                "• 🛡️ <b>시스템 상태:</b> 자동매매 봇은 현금 및 보유 포지션을 안전하게 보존하며 대기 모드를 유지합니다.",
                "• ⏰ <b>다음 정규장:</b> 익일 22:30 KST (09:30 EDT) 정상 개장 예정입니다.",
                "━━━━━━━━━━━━━━━━━━━",
                "💡 <i>휴장일에는 불필요한 매매 신호 연산 및 갭 스캔이 안전하게 건너뛰어집니다.</i>"
            ]
            return "\n".join(lines)

        # 2. Weekend Silence
        if not is_trading:
            logger.info("Today is weekend. Skipping pre-market report.")
            return ""

        # 3. Regular Trading Day Gap Scan
        res = self.scan_gaps()

        lines = [
            f"🌅 <b>[정규장 개장 30분 전 프리마켓 레이더]</b>",
            f"<i>{now_str} KST ({now_ny} 기준)</i>",
            "━━━━━━━━━━━━━━━━━━━",
            "📊 <b>데이터 기준:</b> <code>전일 정규장 공식 종가 vs 당일 프리마켓 실시간 체결가</code>\n"
        ]

        lines.append("💼 <b>보유 종목 프리마켓 현황</b>:")
        if res["held_status"]:
            for h in res["held_status"]:
                sign = "+" if h["gap_pct"] >= 0 else ""
                emoji = "🟢" if h["gap_pct"] >= 0 else "🔴"
                lines.append(f"  • {emoji} <b>{h['symbol']}</b>: ${h['last_price']:.2f} (전일 {h['prev_date']} 종가 대비 <b>{sign}{h['gap_pct']:.2f}%</b>) <i>[{h['quote_time']}]</i>")
        else:
            lines.append("  • 현재 보유 포지션 없음 (100% 현금 대기 중)")

        lines.append("\n🚨 <b>급등락 특이 갭(±3.0% 이상) 포착 종목</b>:")
        if res["gap_alerts"]:
            for g in res["gap_alerts"]:
                sign = "+" if g["gap_pct"] >= 0 else ""
                emoji = "🚀" if g["gap_pct"] > 0 else "⚠️"
                tag = " [★보유중]" if g["is_held"] else ""
                lines.append(f"  • {emoji} <b>{g['symbol']}</b>{tag}: <b>{sign}{g['gap_pct']:.2f}%</b> (${g['prev_close']:.2f} ➔ ${g['last_price']:.2f}) <i>[{g['quote_time']}]</i>")
        else:
            lines.append("  • 특이 갭(±3.0%) 발생 종목 없음 (안정적 보합 출발 예상)")

        lines.append("━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 <i>22:30 KST (09:30 EDT) 정규장 개장 직후 스마트 오더 라우터가 실시간 감시를 개시합니다.</i>")

        return "\n".join(lines)

    def send_alert(self) -> bool:
        """Sends the pre-market gap alert card to Telegram."""
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram credentials missing.")
            return False

        card_text = self.generate_report()
        if not card_text:
            logger.info("Pre-market alert skipped (Not a trading day).")
            return True

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": card_text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }

        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.ok:
                logger.success("Pre-market gap alert sent to Telegram!")
                return True
            else:
                import re
                payload["text"] = re.sub(r'<[^>]+>', '', card_text)
                payload.pop("parse_mode", None)
                requests.post(url, json=payload, timeout=10)
                logger.info("Pre-market alert sent via plain text fallback.")
                return True
        except Exception as e:
            logger.error("Failed to send pre-market alert: {}", e)
            return False

if __name__ == "__main__":
    sentinel = PreMarketGapSentinel()
    sentinel.send_alert()
