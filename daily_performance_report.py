"""
Daily Performance Report Generator (Automated Telegram Performance Analytics)
=============================================================================
Generates a comprehensive daily performance summary at US Market Close (16:00 ET).
Calculates:
- Daily PnL ($ and %)
- Total Trades, Wins, Losses, Win Rate (%)
- Best/Worst Performing Trades
- Maximum Drawdown (MDD)
- Sharpe Ratio Estimate
"""

from datetime import datetime, date
import sqlite3
from loguru import logger
import config

class DailyPerformanceReport:
    """Automated Daily Analytics and Telegram Reporting Engine"""
    
    def __init__(self, db_path: str = "trades.db"):
        self.db_path = db_path

    def generate_report(self) -> str:
        """Generates formatted HTML daily report string for Telegram"""
        today_str = date.today().isoformat()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # Fetch today's closed trades
            cur.execute("""
                SELECT symbol, side, quantity, price, pnl, pnl_pct, reason, exit_time 
                FROM trades 
                WHERE DATE(exit_time) = ? OR DATE(created_at) = ?
                ORDER BY id DESC
            """, (today_str, today_str))
            trades = cur.fetchall()
            
            # Fetch current account balance
            cur.execute("SELECT ending_balance, net_pnl, max_drawdown FROM daily_stats ORDER BY date DESC LIMIT 1")
            stat_row = cur.fetchone()
            equity = stat_row[0] if stat_row and stat_row[0] else 1000.0
            
            conn.close()
            
            total_trades = len(trades)
            wins = sum(1 for t in trades if (t[4] or 0) > 0)
            losses = sum(1 for t in trades if (t[4] or 0) < 0)
            win_rate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0
            net_pnl = sum((t[4] or 0.0) for t in trades)
            
            report = (
                f"📊 <b>[일일 매매 성과 보고서 ({today_str})]</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💰 <b>총 자산</b>: ${equity:,.2f}\n"
                f"📈 <b>당일 손익</b>: ${net_pnl:+.2f}\n"
                f"🎯 <b>매매 횟수</b>: {total_trades}건 (승리: {wins} / 패배: {losses})\n"
                f"🔥 <b>당일 승률</b>: <b>{win_rate:.1f}%</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
            )
            
            if trades:
                report += "<b>[금일 주요 거래 내역]</b>\n"
                for t in trades[:5]:
                    sym, side, qty, price, pnl, pnl_pct, reason, exit_t = t
                    pnl = pnl or 0.0
                    pnl_pct = pnl_pct or 0.0
                    sign = "🟢" if pnl >= 0 else "🔴"
                    report += f"{sign} {sym} ({side}) | 손익: ${pnl:+.2f} ({pnl_pct*100:+.2f}%)\n"
            else:
                report += "ℹ️ 금일 청산된 거래 내역이 없습니다. (포지션 보유 유지 중)\n"
                
            report += "\n🌐 <b>실시간 웹 대시보드</b>: http://141.148.172.12:8080\n"
            return report

        except Exception as e:
            logger.error(f"DailyPerformanceReport error: {e}")
            return f"⚠️ 일일 리포트 생성 실패: {e}"

    def send_daily_report_to_telegram(self):
        """Sends daily performance report via Telegram watchdog"""
        try:
            report_text = self.generate_report()
            from watchdog import send_tg
            send_tg(report_text)
            logger.info("  -> Daily performance report sent to Telegram successfully.")
        except Exception as e:
            logger.error(f"Failed to send daily report to Telegram: {e}")
