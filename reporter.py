"""
Reporter Module - Daily/Weekly Performance Reports
==================================================
Generates performance reports and sends via Telegram.
"""

from datetime import datetime, date, timedelta
from typing import Optional
from loguru import logger
import os
import pytz

from database import get_database, DailyRecord
from notifier import get_notifier


class PerformanceReporter:
    """
    Performance reporting system
    
    Features:
    - Daily P&L summary
    - Weekly performance report
    - Symbol-by-symbol analysis
    - Win rate tracking
    """
    
    def __init__(self):
        self.db = get_database()
        self.notifier = get_notifier()
    
    # ==============================================
    # Daily Report
    # ==============================================
    
    def _us_date(self) -> date:
        """
        US Eastern 기준 날짜.
        만약 장이 끝나기 전(16:00 EST 이전)이면 이전 마지막 영업일을 기준일로 판정하고,
        장이 끝난 후(16:00 EST 이후)이면 당일을 기준일로 판정합니다.
        """
        try:
            from datetime import time
            tz = pytz.timezone('US/Eastern')
            now_est = datetime.now(tz)
            current_date = now_est.date()
            
            if now_est.time() < time(16, 0):
                report_date = current_date - timedelta(days=1)
            else:
                report_date = current_date
                
            from scheduler import TradingScheduler
            scheduler = TradingScheduler()
            while report_date.weekday() >= 5 or report_date.strftime("%Y-%m-%d") in scheduler.HOLIDAYS:
                report_date -= timedelta(days=1)
                
            return report_date
        except Exception as e:
            logger.error("Error calculating US report date: {}", e)
            try:
                return datetime.now(pytz.timezone('US/Eastern')).date()
            except Exception:
                return date.today()
    
    def generate_daily_report(self, d: date = None) -> str:
        """Generate daily performance report including rich dashboard info"""
        d = d or self._us_date()
        
        # 1. Fetch live dashboard data using fetch_dashboard_data.py
        dashboard = {}
        try:
            import subprocess
            import os
            import json
            
            # Find the path to fetch_dashboard_data.py
            base_dir = os.path.dirname(os.path.abspath(__file__))
            fetch_script = os.path.join(base_dir, "fetch_dashboard_data.py")
            
            import sys
            # Needs to run in an environment where it can find the db and config
            python_exe = sys.executable if sys.executable else "python3"
            result = subprocess.run(
                [python_exe, fetch_script], 
                capture_output=True, 
                text=True, 
                cwd=base_dir,
                timeout=20
            )
            
            if result.returncode == 0:
                # The script prints JSON to stdout (sometimes with other prints, so find the last {} block)
                output = result.stdout.strip()
                # Find the last JSON-like block in case there are warnings
                start_idx = output.find('{')
                if start_idx != -1:
                    json_str = output[start_idx:]
                    dashboard = json.loads(json_str)
        except Exception as e:
            logger.error(f"Failed to fetch dashboard data for report: {e}")

        # 2. Get local DB trades (if any completed today)
        trades = self.db.get_trades_today(d)
        if trades:
            sells = [t for t in trades if t.side == "SELL"]
            wins = len([t for t in sells if t.pnl > 0])
            trade_count = len(sells)
        else:
            wins = 0
            trade_count = 0
        win_rate = (wins / trade_count) if trade_count > 0 else 0

        # === 3. BUILD THE MESSAGE ===
        
        # Dashboard values (with fallbacks if fetch failed)
        bp = dashboard.get("buying_power", 0)
        total_val = dashboard.get("total_value", 0)
        Positions = dashboard.get("positions", [])
        
        report = f"📊 <b>DAILY KIS REPORT - {d.strftime('%Y-%m-%d')}</b>\n"
        report += f"━━━━━━━━━━━━━━━━━━\n"
        
        # --- A. Today's Executions ---
        report += "<b>[ 📅 Today's Trades ]</b>\n"
        report += f"• Trades: {trade_count} ({wins}W / {trade_count - wins}L)\n"
        report += f"• Win Rate: {win_rate:.0%}\n\n"

        # --- B. Account Status (from dashboard) ---
        report += "<b>[ 💰 Account Status ]</b>\n"
        exrt = dashboard.get("exchange_rate", 1400.0)
        krw_value = total_val * exrt
        report += f"• Total Value: ${total_val:,.2f} (≈ {krw_value:,.0f} KRW)\n"
        report += f"• Buying Power: ${bp:,.2f}\n"
        
        cagr = dashboard.get("avg_daily_pnl_pct", 0)
        report += f"• Avg Daily Return: {cagr:+.4f}%\n"

        # Overall PnL based on all positions + realized today
        active_pnl = dashboard.get("total_pnl", 0)
        daily_pnl = sum(t.pnl for t in trades if t.side == "SELL") if trades else 0
        emoji = "🟢" if active_pnl >= 0 else "🔴"
        
        report += f"• Open P&L: {emoji} ${active_pnl:,.2f}\n"
        report += f"• Daily Realized: ${daily_pnl:,.2f}\n\n"

        # --- C. Active Positions ---
        report += f"<b>[ 📈 Active Positions ({len(Positions)}) ]</b>\n"
        if not Positions:
            report += "• No active positions.\n"
        else:
            for p in Positions:
                sym = p.get('symbol', 'UNK')
                qty = p.get('qty', 0)
                cur = p.get('current', 0)
                ent = p.get('entry', 0)
                ppnl = p.get('pnl_pct', 0)
                usd_pnl = (cur - ent) * qty
                
                pc = "🟢" if ppnl >= 0 else "🔴"
                report += f"• <code>{sym:5s}</code> | {qty:2d}주 | ${cur:6.2f} | {pc} {ppnl:+.2f}% (<b>${usd_pnl:+,.2f}</b>)\n"

        # --- D. Best/Worst Trades of the day ---
        if trades:
            sells_sorted = sorted([t for t in trades if t.side == "SELL"], key=lambda x: x.pnl, reverse=True)
            if sells_sorted:
                report += "\n<b>[ 🏆 Today's Highlights ]</b>\n"
                best = sells_sorted[0]
                report += f"🥇 Best: <code>{best.symbol:5s}</code> ${best.pnl:+,.2f} ({best.pnl_pct:+.1%})\n"
                if len(sells_sorted) > 1:
                    worst = sells_sorted[-1]
                    report += f"💀 Worst: <code>{worst.symbol:5s}</code> ${worst.pnl:+,.2f} ({worst.pnl_pct:+.1%})\n"

        report += f"━━━━━━━━━━━━━━━━━━"
        return report.strip()
    
    def send_daily_summary(self):
        """Send daily report via Telegram (only once per day)"""
        us_d = self._us_date()
        
        # Prevent duplicates
        if self.db.is_report_sent("DAILY_SUMMARY", us_d):
            logger.info("Daily summary already sent for {}. Skipping.", us_d)
            return
            
        report = self.generate_daily_report(us_d)
        
        # Get today's stats
        trades = self.db.get_trades_today(us_d)
        sells = [t for t in trades if t.side == "SELL"]
        
        chart_path = ""
        try:
            from chart_generator import generate_daily_pnl_chart
            chart_path = generate_daily_pnl_chart(days=90)
        except Exception as e:
            logger.warning("Chart generation failed safely: {}", e)
            
        success = False
        try:
            if chart_path and hasattr(self.notifier, 'send_photo_sync'):
                success = self.notifier.send_photo_sync(photo_path=chart_path, caption=report)
            elif hasattr(self.notifier, 'send_sync'):
                success = self.notifier.send_sync(report)
            else:
                # Fallback to async if sync method doesn't exist
                if chart_path and hasattr(self.notifier, 'send_photo'):
                    self.notifier.send_photo(photo_path=chart_path, caption=report)
                else:
                    self.notifier.send(report)
                success = True # Assume success to preserve legacy behavior
        except Exception as e:
            logger.error("Notifier failed to push daily report: {}", e)
            
        if success:
            # Mark as sent only when transmission actually succeeded
            self.db.mark_report_sent("DAILY_SUMMARY", us_d)
            logger.info("Daily report successfully sent and marked in database for {}", us_d)
        else:
            logger.warning("Daily report sending failed. Database mark skipped to allow retry.")

    def send_yearly_report(self):
        """Send 1-year performance report with chart"""
        from chart_generator import generate_daily_pnl_chart
        
        # Explicitly request 365 days
        chart_path = generate_daily_pnl_chart(days=365)
        
        # Summary text for yearly report
        # Get total realized P&L from all time
        try:
            row = self.db.execute("SELECT SUM(pnl) as net_pnl FROM trades WHERE side = 'SELL' AND pnl IS NOT NULL").fetchone()
            total_realized = row["net_pnl"] if row and row["net_pnl"] else 0
        except:
            total_realized = 0
            
        report = f"📅 <b>KIS ANNUAL PERFORMANCE REPORT</b>\n"
        report += f"━━━━━━━━━━━━━━━━━━\n"
        report += f"• Period: Last 365 Days\n"
        report += f"• Realized P&L: <b>${total_realized:+,.2f}</b>\n"
        report += f"━━━━━━━━━━━━━━━━━━"
        
        if chart_path and os.path.exists(chart_path) and hasattr(self.notifier, 'send_photo'):
            self.notifier.send_photo(photo_path=chart_path, caption=report)
            logger.info(f"Yearly report sent with chart: {chart_path}")
        else:
            self.notifier.send_all(report)
            logger.warning("Yearly report sent (text only) - chart omitted")
    
    # ==============================================
    # Weekly Report
    # ==============================================
    
    def generate_weekly_report(self) -> str:
        """Generate weekly performance report (Korean, rich format)"""
        # US Eastern 기준 주교 난일들 수집
        weekly_stats = self.db.get_weekly_stats()

        if not weekly_stats:
            return "📥 이번 주 거래 데이터가 없습니다."

        total_trades = sum(s.trades_count for s in weekly_stats)
        total_wins   = sum(s.wins        for s in weekly_stats)
        total_pnl    = sum(s.net_pnl     for s in weekly_stats)
        win_rate     = total_wins / max(total_trades, 1)

        best_day  = max(weekly_stats, key=lambda x: x.net_pnl)
        worst_day = min(weekly_stats, key=lambda x: x.net_pnl)

        period_start = weekly_stats[-1].date.strftime('%m/%d')
        period_end   = weekly_stats[0].date.strftime('%m/%d')
        pnl_emoji    = "💰" if total_pnl >= 0 else "🔻"
        wr_emoji     = "🟢" if win_rate >= 0.5 else "🔴"

        report  = f"{pnl_emoji} <b>주간 매매 리포트 ({period_start} ~ {period_end})</b>\n"
        report += f"━" * 18 + "\n"
        report += f"📅 거래일수: {len(weekly_stats)}일\n"
        report += f"📊 총 거래: {total_trades}건 ("
        report += f"{total_wins}승/{total_trades - total_wins}패)\n"
        report += f"{wr_emoji} 승률: {win_rate:.0%}\n"
        report += f"{pnl_emoji} 주간 순손익: <b>${total_pnl:+,.2f}</b>\n"
        report += f"━" * 18 + "\n"
        report += f"🏆 최고의 날: {best_day.date.strftime('%m/%d')} "
        report += f"<b>${best_day.net_pnl:+,.2f}</b>\n"
        report += f"💣 최악의 날: {worst_day.date.strftime('%m/%d')} "
        report += f"<b>${worst_day.net_pnl:+,.2f}</b>\n"
        report += f"━" * 18 + "\n"
        report += "<b>[🗓 일별 실적]</b>\n"
        for s in reversed(weekly_stats):  # 오래된 날짜부터 표시
            emoji = "🟢" if s.net_pnl >= 0 else "🔴"
            report += (
                f"{emoji} {s.date.strftime('%m/%d(%a)')}: "
                f"<b>${s.net_pnl:+,.2f}</b> ({s.trades_count}건)\n"
            )

        return report.strip()

    def send_weekly_report(self):
        """Send weekly report via Telegram (Monday only, once per week)"""
        us_today = self._us_date()
        # Monday = 0 (weekday)
        if us_today.weekday() != 0:
            logger.debug("Weekly report skipped (월요일이 아님: {})", us_today)
            return

        # 중복 발송 방지 — 이번 주 월요일에 이미 보냈으면 건너뜀
        if self.db.is_report_sent("WEEKLY_SUMMARY", us_today):
            logger.info("Weekly summary already sent for {}. Skipping.", us_today)
            return

        report = self.generate_weekly_report()
        success = False
        try:
            if hasattr(self.notifier, 'send_sync'):
                success = self.notifier.send_sync(report)
            else:
                self.notifier.send(report)
                success = True
        except Exception as e:
            logger.error("Weekly report send failed: {}", e)
            
        if success:
            self.db.mark_report_sent("WEEKLY_SUMMARY", us_today)
            logger.info("Weekly report successfully sent and marked in database for week ending {}", us_today)
        else:
            logger.warning("Weekly report sending failed. Database mark skipped to allow retry.")
    
    # ==============================================
    # Symbol Analysis
    # ==============================================
    
    def get_symbol_performance(self, symbol: str) -> str:
        """Get performance for a specific symbol"""
        stats = self.db.get_symbol_stats(symbol)
        
        return f"""
📊 {symbol} Performance
{'━' * 25}
Trades: {stats['trades']}
Win Rate: {stats['win_rate']:.0%}
Total P&L: ${stats['total_pnl']:+,.2f}
Avg P&L: {stats['avg_pnl_pct']:+.1%}
"""
    
    def get_top_performers(self, limit: int = 5) -> str:
        """Get top performing symbols"""
        # Get unique symbols traded
        trades = self.db.get_trades_range(
            date.today() - timedelta(days=30),
            date.today()
        )
        
        symbols = set(t.symbol for t in trades)
        
        # Get stats for each
        symbol_stats = []
        for sym in symbols:
            stats = self.db.get_symbol_stats(sym)
            if stats['trades'] > 0:
                symbol_stats.append(stats)
        
        # Sort by total P&L
        symbol_stats.sort(key=lambda x: x['total_pnl'], reverse=True)
        
        report = "🏆 Top Performers (30 days)\n" + "━" * 25 + "\n"
        
        for i, s in enumerate(symbol_stats[:limit], 1):
            emoji = "🟢" if s['total_pnl'] >= 0 else "🔴"
            report += f"{i}. {emoji} {s['symbol']}: ${s['total_pnl']:+,.2f} ({s['win_rate']:.0%})\n"
        
        return report


# Global instance
_reporter = None

def get_reporter() -> PerformanceReporter:
    global _reporter
    if _reporter is None:
        _reporter = PerformanceReporter()
    return _reporter


# Alias for backward compatibility
TradingReporter = PerformanceReporter


if __name__ == "__main__":
    print("Testing PerformanceReporter...")
    reporter = PerformanceReporter()
    
    print("\n" + reporter.generate_daily_report())
    print("\n" + reporter.generate_weekly_report())
