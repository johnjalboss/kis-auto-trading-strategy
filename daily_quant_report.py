"""
Daily Quant Portfolio Report Card (daily_quant_report.py)
=========================================================
Generates and delivers an institutional daily portfolio summary report card
to Telegram at US Market Close (06:05 KST).
"""

import os
import sqlite3
import requests
from datetime import datetime, date
from typing import Dict, Any, List
from loguru import logger
import config

class DailyQuantReportCard:
    """Delivers daily closing performance scorecard to Telegram"""

    def __init__(self, db_path: str = "trades.db"):
        self.db_path = db_path if os.path.exists(db_path) else "/home/ubuntu/kis-auto-trading/trades.db"
        self.bot_token = getattr(config, 'TELEGRAM_BOT_TOKEN', '')
        self.chat_id = getattr(config, 'TELEGRAM_CHAT_ID', '')

    def _send_telegram(self, text: str):
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram token or chat_id not configured for daily report.")
            return
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                logger.info("✅ Daily Quant Report Card sent to Telegram successfully.")
            else:
                logger.warning("Telegram send failed: {} {}", resp.status_code, resp.text)
        except Exception as e:
            logger.error("Failed to send Daily Quant Report: {}", e)

    def generate_and_send_report(self, trader_instance=None) -> Dict[str, Any]:
        """Gathers positions, trades, buying power, and sends summary report"""
        try:
            from trader import get_trader
            tr = trader_instance or get_trader()
            buying_power = tr.get_buying_power()
            positions = tr.get_positions()
        except Exception:
            buying_power = 0.0
            positions = []

        total_pos_val = sum(p.quantity * p.current_price for p in positions)
        total_equity = buying_power + total_pos_val

        # Query today's realized trades from DB
        today_trades = []
        today_realized_pnl = 0.0
        wins = 0
        losses = 0
        if os.path.exists(self.db_path):
            try:
                conn = sqlite3.connect(self.db_path)
                cur = conn.cursor()
                today_str = date.today().isoformat()
                rows = cur.execute("""
                    SELECT symbol, side, quantity, price, pnl, pnl_pct, reason, exit_time
                    FROM trades
                    WHERE DATE(exit_time) = ? OR DATE(created_at) = ?
                    ORDER BY id DESC
                """, (today_str, today_str)).fetchall()
                for r in rows:
                    pnl_val = float(r[4] or 0.0)
                    today_realized_pnl += pnl_val
                    if pnl_val >= 0:
                        wins += 1
                    else:
                        losses += 1
                    today_trades.append({
                        "symbol": r[0], "side": r[1], "qty": r[2], "price": r[3],
                        "pnl": pnl_val, "pnl_pct": float(r[5] or 0.0), "reason": r[6]
                    })
                conn.close()
            except Exception as _db_err:
                logger.debug("DB trades query for daily report skipped: {}", _db_err)

        # Get Macro Regime
        regime = "BULL_NORMAL"
        try:
            from macro import get_macro_data
            m_data = get_macro_data()
            if m_data:
                regime = getattr(m_data, 'regime', 'BULL_NORMAL')
        except Exception:
            pass

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M KST")
        
        # Build Telegram Message
        msg = f"🏆 <b>[월스트리트 AI 퀀트 일일 장 마감 성적표]</b>\n"
        msg += f"📅 <i>기준일시: {now_str} (미국 정규장 마감)</i>\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"🌐 <b>시장 국면(Regime):</b> <code>{regime}</code>\n"
        msg += f"💵 <b>총 계좌 자산:</b> <b>${total_equity:.2f}</b>\n"
        msg += f"   • 보유 주식 평가액: ${total_pos_val:.2f}\n"
        msg += f"   • 매수 가능 예수금: ${buying_power:.2f}\n\n"

        msg += f"📊 <b>[보유 5대 포지션 실시간 현황]</b>\n"
        if positions:
            for p in positions:
                pnl_pct = ((p.current_price - p.avg_price) / p.avg_price * 100.0) if p.avg_price > 0 else 0.0
                pnl_icon = "🟢" if pnl_pct >= 0 else "🔴"
                msg += f"{pnl_icon} <b>{p.symbol}</b>: {p.quantity}주 @ ${p.current_price:.2f} (<b>{pnl_pct:+.2f}%</b>)\n"
                msg += f"   └ 매수가: ${p.avg_price:.2f} | 평가액: ${p.quantity * p.current_price:.2f}\n"
        else:
            msg += f"   <i>현재 전액 현금 보유 중 (리스크 관리)</i>\n"

        msg += f"\n💰 <b>[오늘 실현 손익 결산]</b>\n"
        win_rate = (wins / (wins + losses) * 100.0) if (wins + losses) > 0 else 0.0
        realized_icon = "🎉" if today_realized_pnl >= 0 else "🛡️"
        msg += f"{realized_icon} 당일 실현 손익: <b>${today_realized_pnl:+.2f}</b> (총 {len(today_trades)}건 체결)\n"
        if today_trades:
            msg += f"🎯 승률: <b>{win_rate:.1f}%</b> (승: {wins} | 패: {losses})\n"
        
        msg += f"━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"🤖 <i>AI 퀀트 봇이 24시간 무인으로 계좌 수익을 안전하게 관리 중입니다.</i>"

        self._send_telegram(msg)
        return {
            "total_equity": total_equity,
            "today_pnl": today_realized_pnl,
            "positions_count": len(positions)
        }

def get_daily_quant_report_card() -> DailyQuantReportCard:
    return DailyQuantReportCard()

if __name__ == "__main__":
    rep = DailyQuantReportCard()
    res = rep.generate_and_send_report()
    print("Report result:", res)
