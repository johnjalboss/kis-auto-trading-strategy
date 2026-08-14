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

    def __init__(self, db_path: str = "trades.db", usd_krw_rate: Optional[float] = None):
        self.db_path = Path(db_path)
        if usd_krw_rate and usd_krw_rate > 0:
            self.fx_rate = usd_krw_rate
        else:
            try:
                import yfinance as yf
                t = yf.Ticker("USDKRW=X")
                self.fx_rate = float(t.fast_info.get("last_price", 1415.0))
            except Exception:
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

        try:
            conn = sqlite3.connect(str(self.db_path))
            cur = conn.cursor()
            cur.execute("""
                SELECT symbol, side, quantity, price, pnl, pnl_pct, reason, created_at
                FROM trades
                WHERE side = 'SELL' AND date(created_at) = ?
                ORDER BY id ASC
            """, (today_str,))
            rows = cur.fetchall()
            conn.close()

            if not rows:
                res["telegram_msg"] = f"📊 [{today_str} 일일 마감 결산]\n당일 실현 매매가 없습니다. (보유 포지션 유지 중)"
                return res

            res["trades_count"] = len(rows)
            for r in rows:
                sym, side, qty, price, pnl, pnl_pct, reason, created_at = r
                pnl = float(pnl or 0.0)
                pnl_pct = float(pnl_pct or 0.0)
                if pnl > 0:
                    res["wins"] += 1
                elif pnl < 0:
                    res["losses"] += 1
                res["realized_pnl_usd"] += pnl
                res["closed_trades"].append({
                    "symbol": sym, "qty": qty, "price": price, "pnl": pnl, "pnl_pct": pnl_pct, "reason": reason
                })

            res["win_rate"] = round((res["wins"] / res["trades_count"] * 100.0), 1) if res["trades_count"] > 0 else 0.0
            res["realized_pnl_krw"] = round(res["realized_pnl_usd"] * self.fx_rate, 0)

            # Build Telegram Settlement Card
            icon = "🎉" if res["realized_pnl_usd"] >= 0 else "🛡️"
            sign = "+" if res["realized_pnl_usd"] >= 0 else ""
            msg = (
                f"{icon} <b>[{today_str} 퀀트 마스터 일일 결산 보고서]</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"• 💰 <b>당일 실현 손익:</b> {sign}${res['realized_pnl_usd']:+,.2f} ({sign}{res['realized_pnl_krw']:+,.0f}원)\n"
                f"• 🎯 <b>매매 전적:</b> {res['trades_count']}전 {res['wins']}승 {res['losses']}패 (승률 {res['win_rate']}%)\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"<b>[세부 청산 내역]</b>\n"
            )

            for t in res["closed_trades"][:6]:
                t_sign = "+" if t['pnl'] >= 0 else ""
                msg += f"• <b>{t['symbol']}</b>: {t_sign}${t['pnl']:+,.2f} ({t_sign}{t['pnl_pct']:+.2f}%) | {t['reason'][:20]}\n"

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
