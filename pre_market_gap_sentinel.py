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
        symbols = []
        if os.path.exists(self.db_path):
            try:
                conn = sqlite3.connect(self.db_path)
                cur = conn.cursor()
                cur.execute("SELECT symbol FROM positions WHERE quantity > 0")
                symbols = [row[0] for row in cur.fetchall()]
                conn.close()
            except Exception as e:
                logger.debug("Failed to fetch positions: {}", e)
        if not symbols:
            symbols = ["MDT", "STRC", "VTOL", "MRK"]
        return symbols

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

        # 2. Try loading active screener candidates
        try:
            from screener import DynamicScreener
            from macro import MarketRegime
            res = DynamicScreener().screen(regime=MarketRegime.RISK_ON)
            if res and res.tickers:
                for t in res.tickers[:12]:
                    if t not in candidates:
                        candidates.append(t)
        except Exception as e:
            logger.debug("Screener candidates fetch skipped: {}", e)

        # 3. High-Momentum Growth & Breakout Leaders (Dynamic Universe Pool)
        growth_leaders = ["NVDA", "PLTR", "LLY", "VRT", "CRWD", "APP", "AXON", "GEV", "TSLA", "AMD"]
        for sym in growth_leaders:
            if len(candidates) >= 16:
                break
            if sym not in candidates:
                candidates.append(sym)

        return candidates

    def scan_gaps(self, threshold_pct: float = 3.0) -> dict:
        """Scan held positions and top universe stocks for pre-market gaps."""
        held = self.get_held_symbols()
        watchlist = self.get_dynamic_watchlist()
        all_symbols = list(dict.fromkeys(held + watchlist))

        gap_alerts = []
        held_status = []

        for sym in all_symbols:
            try:
                t = yf.Ticker(sym)
                fast = t.fast_info
                last_price = float(fast.get("last_price", 0.0) or 0.0)
                prev_close = float(fast.get("previous_close", 0.0) or 0.0)

                if last_price <= 0 or prev_close <= 0:
                    df = yf.download(sym, period="5d", progress=False)
                    if not df.empty:
                        if isinstance(df.columns, pd.MultiIndex):
                            df.columns = df.columns.get_level_values(0)
                        last_price = float(df['Close'].iloc[-1])
                        prev_close = float(df['Close'].iloc[-2]) if len(df) >= 2 else last_price

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
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        lines = [
            f"🌅 <b>[정규장 개장 30분 전 프리마켓 레이더]</b>",
            f"<i>{now_str} KST (Pre-Market Gap Sentinel)</i>",
            "━━━━━━━━━━━━━━━━━━━",
            "💼 <b>보유 종목 프리마켓 현황</b>:"
        ]

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
        lines.append("💡 <i>23:30 정규장 개장 직후 스마트 오더 라우터가 실시간 감시를 개시합니다.</i>")

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
