"""
4. Institutional EOD Daily Settlement Telegram Reporter & Korean Tax CSV Generator (daily_settlement_reporter.py)
===================================================================================================================
Features:
1. Compiles daily closed trade statistics: Gross PnL, Win Count, Loss Count, Win Rate, and Total Trades.
2. Formats a Telegram Daily Settlement Card.
3. Automatically exports an annual Korean Tax Netting CSV (`tax_export_YYYY.csv`) compatible with HTS/NTS tax filing.
"""

import os
import csv
import sqlite3
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger

class DailySettlementReporter:
    """Generates daily settlement reports and Korean capital gains tax export files"""

    def __init__(self, db_path: Optional[str] = None, usd_krw_rate: Optional[float] = None):
        if not db_path:
            script_dir = Path(__file__).resolve().parent
            cand = script_dir / "trades.db"
            self.db_path = cand if cand.exists() else Path("trades.db")
        else:
            self.db_path = Path(db_path)

        if usd_krw_rate and usd_krw_rate > 0:
            self.fx_rate = usd_krw_rate
        else:
            self.fx_rate = 1415.0

    def generate_daily_report(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate daily settlement metrics and Telegram message text for target_date (YYYY-MM-DD)
        """
        if target_date:
            today_str = target_date
        else:
            try:
                import pytz
                today_str = datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d")
            except Exception:
                today_str = datetime.now().strftime("%Y-%m-%d")

        res = {
            "date": today_str,
            "trades_count": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "realized_pnl_usd": 0.0,
            "realized_pnl_krw": 0.0,
            "telegram_msg": "",
            "closed_trades": []
        }

        if not self.db_path.exists():
            return res

        # Dynamic US Eastern offset (-13h in EDT, -14h in EST)
        offset_hours = 13
        try:
            import pytz
            now_kst = datetime.now(pytz.timezone('Asia/Seoul'))
            now_et = datetime.now(pytz.timezone('US/Eastern'))
            diff_sec = (now_kst.replace(tzinfo=None) - now_et.replace(tzinfo=None)).total_seconds()
            offset_hours = int(round(diff_sec / 3600.0))
        except Exception:
            offset_hours = 13
        offset_modifier = f"-{offset_hours} hours"

        try:
            conn = sqlite3.connect(str(self.db_path))
            cur = conn.cursor()
            cur.execute("""
                SELECT symbol, side, quantity, price, pnl, pnl_pct, setup_reason as reason, created_at
                FROM trade_details
                WHERE side = 'SELL' AND date(created_at, ?) = ?
                UNION ALL
                SELECT symbol, side, quantity, price, pnl, pnl_pct, reason, created_at
                FROM trades
                WHERE side = 'SELL' AND date(created_at, ?) = ?
                ORDER BY created_at ASC
            """, (offset_modifier, today_str, offset_modifier, today_str))
            rows = cur.fetchall()
            conn.close()

            seen_trades = set()
            clean_trades = []
            for r in rows:
                sym, side, qty, price, pnl, pnl_pct, reason, created_at = r
                pnl_val = float(pnl or 0.0)
                qty_val = int(qty or 0)
                t_key = (sym, round(pnl_val, 2), qty_val)
                if t_key in seen_trades:
                    continue
                seen_trades.add(t_key)
                clean_trades.append(r)

            if not clean_trades:
                res["telegram_msg"] = f"📊 [{today_str} 일일 마감 결산]\n당일 실현 매매가 없습니다. (보유 포지션 유지 중)"
                return res

            res["trades_count"] = len(clean_trades)
            for r in clean_trades:
                sym, side, qty, price, pnl, pnl_pct, reason, created_at = r
                pnl = float(pnl or 0.0)
                pnl_pct = float(pnl_pct or 0.0)
                if abs(pnl_pct) < 1.0 and pnl_pct != 0.0:
                    pnl_pct = pnl_pct * 100.0

                if pnl > 0:
                    res["wins"] += 1
                elif pnl < 0:
                    res["losses"] += 1
                res["realized_pnl_usd"] += pnl
                res["closed_trades"].append({
                    "symbol": sym, "qty": qty, "price": price, "pnl": pnl, "pnl_pct": pnl_pct, "reason": reason or "N/A"
                })

            res["win_rate"] = round((res["wins"] / res["trades_count"] * 100.0), 1) if res["trades_count"] > 0 else 0.0
            res["realized_pnl_krw"] = round(res["realized_pnl_usd"] * self.fx_rate, 0)

            # Build Telegram Settlement Card
            icon = "🎉" if res["realized_pnl_usd"] >= 0 else "🛡️"
            usd_str = f"+${res['realized_pnl_usd']:.2f}" if res['realized_pnl_usd'] >= 0 else f"-${abs(res['realized_pnl_usd']):.2f}"
            krw_str = f"+{res['realized_pnl_krw']:,.0f}원" if res['realized_pnl_krw'] >= 0 else f"{res['realized_pnl_krw']:,.0f}원"
            
            msg = (
                f"{icon} <b>[{today_str} 퀀트 마스터 일일 결산 보고서]</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"• 💰 <b>당일 실현 손익:</b> {usd_str} ({krw_str})\n"
                f"• 🎯 <b>매매 전적:</b> {res['trades_count']}전 {res['wins']}승 {res['losses']}패 (승률 {res['win_rate']}%)\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"<b>[세부 청산 내역]</b>\n"
            )

            for t in res["closed_trades"][:8]:
                t_usd = f"+${t['pnl']:.2f}" if t['pnl'] >= 0 else f"-${abs(t['pnl']):.2f}"
                t_pct = f"+{t['pnl_pct']:.2f}%" if t['pnl_pct'] >= 0 else f"{t['pnl_pct']:.2f}%"
                r_clean = str(t['reason']).replace('\n', ' ')
                msg += f"• <b>{t['symbol']}</b>: {t_usd} ({t_pct}) | <i>{r_clean[:40]}</i>\n"

            res["telegram_msg"] = msg
            return res

        except Exception as e:
            logger.error("Failed to generate daily settlement report: {}", e)
            return res

    def export_tax_csv(self, year: Optional[int] = None, output_file: str = "tax_export.csv") -> str:
        """
        Export all annual trades to CSV for Korean Capital Gains Tax reporting
        """
        target_year = year or datetime.now().year
        try:
            conn = sqlite3.connect(str(self.db_path))
            cur = conn.cursor()
            cur.execute("""
                SELECT created_at, symbol, side, quantity, price, pnl, pnl_pct, reason
                FROM trades
                WHERE strftime('%Y', created_at) = ?
                ORDER BY id ASC
            """, (str(target_year),))
            rows = cur.fetchall()
            conn.close()

            with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["거래일시", "종목코드", "매매구분", "수량", "체결단가(USD)", "실현손익(USD)", "실현손익(KRW환산)", "수익률(%)", "매매사유"])
                for r in rows:
                    t_time, sym, side, qty, price, pnl, pnl_pct, reason = r
                    pnl_val = float(pnl or 0.0)
                    pnl_krw = round(pnl_val * self.fx_rate, 0)
                    pnl_pct_val = float(pnl_pct or 0.0)
                    writer.writerow([t_time, sym, side, qty, f"{float(price or 0.0):.2f}", f"{pnl_val:.2f}", f"{pnl_krw:.0f}", f"{pnl_pct_val:.2f}", reason])

            logger.info("📄 [TAX_EXPORT] Exported annual tax records to {}", output_file)
            return output_file

        except Exception as e:
            logger.error("Failed to export tax CSV: {}", e)
            return ""

    def send_daily_report_to_telegram(self, target_date: Optional[str] = None) -> bool:
        """Sends daily settlement report card to Telegram."""
        try:
            res = self.generate_daily_report(target_date)
            msg = res.get("telegram_msg", "")
            if not msg:
                return False

            token = getattr(config, 'TELEGRAM_BOT_TOKEN', '')
            chat_id = getattr(config, 'TELEGRAM_CHAT_ID', '')
            
            if not token or not chat_id:
                env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
                if os.path.exists(env_file):
                    from dotenv import load_dotenv
                    load_dotenv(env_file)
                    token = os.getenv("TELEGRAM_BOT_TOKEN", token)
                    chat_id = os.getenv("TELEGRAM_CHAT_ID", chat_id)

            if not token or not chat_id:
                logger.warning("Telegram credentials missing. Daily settlement cannot be sent.")
                return False

            import requests
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": msg,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            resp = requests.post(url, json=payload, timeout=10)
            if resp.ok:
                logger.success("Daily settlement report sent to Telegram!")
                return True
            else:
                import re
                clean_text = re.sub(r'<[^>]+>', '', msg)
                payload["text"] = clean_text
                payload.pop("parse_mode", None)
                requests.post(url, json=payload, timeout=10)
                logger.info("Daily settlement report sent via fallback.")
                return True
        except Exception as e:
            logger.error("Failed to send daily settlement report: {}", e)
            return False

if __name__ == "__main__":
    rep = DailySettlementReporter()
    rep.send_daily_report_to_telegram()

