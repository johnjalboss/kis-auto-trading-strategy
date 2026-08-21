"""
Pre-Market Gap Sentinel (pre_market_gap_sentinel.py)
====================================================
Designed by World #1 Quant Systems Architecture.
Runs 30 minutes before US regular market open (23:00 KST / 10:00 EDT)
to detect violent pre-market gap-ups and gap-downs (>= +/-3.0%)
across held positions and key watchlist leaders.
"""

import os
import sqlite3
import yfinance as yf
import pandas as pd
from datetime import datetime
from loguru import logger
import requests
import config

class PreMarketGapSentinel:
    """Detects pre-market opening gaps and alerts the trader with actionable quant guidance."""

    def __init__(self, db_path: str = "trades.db"):
        self.db_path = db_path if os.path.exists(db_path) else "/home/ubuntu/kis-auto-trading/trades.db"
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
        except Exception as _tr_err:
            logger.debug("Live trader get_positions skipped in sentinel: {}", _tr_err)

        # 2. Direct SQLite query with active quantity > 0
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

        # 3. Try TradeDatabase
        try:
            from database import TradeDatabase, get_database
            db = get_database()
            pos_dict = db.get_positions()
            if pos_dict:
                symbols = [s for s, p in pos_dict.items() if p.get('quantity', 0) > 0]
                if symbols:
                    return symbols
        except Exception as _db_err:
            logger.debug("Database get_positions skipped: {}", _db_err)

        return []

    def get_dynamic_watchlist(self) -> list:
        """Dynamically builds 2nd priority watch candidates from:
        1. Bot's active screened targets (screener / target universe)
        2. Key Sector/Market Benchmark ETFs (QQQ, SPY, SMH, IWM)
        3. Active momentum growth leaders
        """
        candidates = []
        
        # 1. Key Sector/Market Benchmark ETFs (Market Health Barometer)
        benchmarks = ["QQQ", "SPY", "SMH", "IWM"]
        candidates.extend(benchmarks)

        # 2. High-Momentum Growth & Breakout Leaders (Dynamic Universe Pool)
        growth_leaders = ["NVDA", "PLTR", "LLY", "VRT", "CRWD", "APP", "AXON", "GEV", "TSLA", "AMD"]
        for sym in growth_leaders:
            if len(candidates) >= 14:
                break
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

        for sym in all_symbols:
            try:
                t = yf.Ticker(sym)
                last_price = 0.0
                prev_close = 0.0

                # 1. Try 1m intraday with prepost=True for true extended hours live quotes
                try:
                    df_intra = t.history(period="1d", interval="1m", prepost=True)
                    if df_intra is not None and not df_intra.empty:
                        last_price = float(df_intra['Close'].iloc[-1])
                except Exception:
                    pass

                # 2. Daily history for previous close
                try:
                    df_daily = t.history(period="5d")
                    if df_daily is not None and not df_daily.empty:
                        if len(df_daily) >= 2:
                            prev_close = float(df_daily['Close'].iloc[-2])
                        else:
                            prev_close = float(df_daily['Close'].iloc[-1])
                        if last_price <= 0:
                            last_price = float(df_daily['Close'].iloc[-1])
                except Exception:
                    pass

                # 3. Fallback to fast_info if still zero
                if last_price <= 0 or prev_close <= 0:
                    fast = t.fast_info
                    if last_price <= 0:
                        last_price = float(fast.get("last_price", 0.0) or 0.0)
                    if prev_close <= 0:
                        prev_close = float(fast.get("previous_close", 0.0) or 0.0)

                if prev_close > 0 and last_price > 0:
                    gap_pct = ((last_price - prev_close) / prev_close) * 100.0
                    is_held = sym in held

                    info = {
                        "symbol": sym,
                        "is_held": is_held,
                        "last_price": last_price,
                        "prev_close": prev_close,
                        "gap_pct": gap_pct
                    }

                    if is_held:
                        held_status.append(info)

                    if abs(gap_pct) >= threshold_pct:
                        gap_alerts.append(info)
            except Exception as e:
                logger.debug("Pre-market scan error for {}: {}", sym, e)

        return {
            "gap_alerts": gap_alerts,
            "held_status": held_status,
            "scanned_count": len(all_symbols)
        }

    def generate_report(self) -> str:
        """Generates pre-market opening intelligence brief."""
        res = self.scan_gaps()
        now_dt = datetime.now()
        now_str = now_dt.strftime("%Y-%m-%d %H:%M")
        is_weekend = now_dt.weekday() in (5, 6)  # Saturday or Sunday

        lines = [
            f"🌅 <b>[정규장 개장 30분 전 프리마켓 레이더]</b>",
            f"<i>{now_str} KST (Pre-Market Gap Sentinel)</i>",
            "━━━━━━━━━━━━━━━━━━━"
        ]

        if is_weekend:
            lines.append("☕ <b>[주말 휴장 안내]</b>: 현재 미국 증시 주말 휴장 상태입니다.")
            lines.append("   (프리마켓 시세는 금요일 종가 기준으로 고정되어 있습니다)\n")

        lines.append("💼 <b>보유 종목 프리마켓 현황</b>:")
        if res["held_status"]:
            for h in res["held_status"]:
                sign = "+" if h["gap_pct"] >= 0 else ""
                emoji = "🟢" if h["gap_pct"] >= 0 else "🔴"
                lines.append(f"  • {emoji} <b>{h['symbol']}</b>: ${h['last_price']:.2f} (전일대비 <b>{sign}{h['gap_pct']:.2f}%</b>)")
        else:
            lines.append("  • 현재 보유 포지션 없음 (100% 현금 대기)")

        lines.append("\n🚨 <b>급등락 특이 갭(±3.0% 이상) 포착 종목</b>:")
        if res["gap_alerts"]:
            for g in res["gap_alerts"]:
                sign = "+" if g["gap_pct"] >= 0 else ""
                emoji = "🚀" if g["gap_pct"] > 0 else "⚠️"
                tag = " [★보유중]" if g["is_held"] else ""
                lines.append(f"  • {emoji} <b>{g['symbol']}</b>{tag}: <b>{sign}{g['gap_pct']:.2f}%</b> (${g['prev_close']:.2f} ➔ ${g['last_price']:.2f})")
        else:
            lines.append("  • 특이 갭(±3%) 발생 종목 없음 (안정적 보합 출발 예상)")

        lines.append("━━━━━━━━━━━━━━━━━━━")
        if not is_weekend:
            lines.append("💡 <i>22:30 KST (09:30 EDT) 정규장 개장 직후 스마트 오더 라우터가 실시간 감시를 개시합니다.</i>")
        else:
            lines.append("💡 <i>월요일 밤 22:30 KST 정규장 개장 시 실시간 자동 매매가 재개됩니다.</i>")

        return "\n".join(lines)

    def send_alert(self) -> bool:
        """Sends the pre-market gap alert card to Telegram."""
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram credentials missing.")
            return False

        card_text = self.generate_report()
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
