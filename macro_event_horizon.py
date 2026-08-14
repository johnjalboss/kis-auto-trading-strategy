"""
Macro Event Horizon & Earnings D-Day Countdown Radar (v1.0.0)
=============================================================
Tracks high-impact US macro events (CPI, FOMC, NFP) and portfolio earnings dates.
Provides automated risk-shield recommendations (e.g. 50% sizing cut on D-0/D-1)
and formatted Telegram D-Day briefing cards.
"""

import os
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from loguru import logger
import config

# Pre-programmed 2026 Key US Macro Events Calendar (Y-M-D)
MACRO_CALENDAR_2026 = [
    # CPI Releases (8:30 AM ET)
    {"date": "2026-08-12", "name": "미국 7월 CPI (소비자물가지수)", "impact": "HIGH", "type": "CPI"},
    {"date": "2026-09-11", "name": "미국 8월 CPI (소비자물가지수)", "impact": "HIGH", "type": "CPI"},
    {"date": "2026-10-14", "name": "미국 9월 CPI (소비자물가지수)", "impact": "HIGH", "type": "CPI"},
    {"date": "2026-11-12", "name": "미국 10월 CPI (소비자물가지수)", "impact": "HIGH", "type": "CPI"},
    {"date": "2026-12-11", "name": "미국 11월 CPI (소비자물가지수)", "impact": "HIGH", "type": "CPI"},
    
    # FOMC Interest Rate Decisions (2:00 PM ET)
    {"date": "2026-09-16", "name": "FOMC 기준금리 결정 & 점도표 발표", "impact": "CRITICAL", "type": "FOMC"},
    {"date": "2026-11-05", "name": "FOMC 기준금리 결정", "impact": "CRITICAL", "type": "FOMC"},
    {"date": "2026-12-16", "name": "FOMC 기준금리 결정 & 경제전망", "impact": "CRITICAL", "type": "FOMC"},

    # Non-Farm Payrolls (First Friday of month, 8:30 AM ET)
    {"date": "2026-09-04", "name": "미국 8월 비농업 고용보고서 (NFP)", "impact": "HIGH", "type": "NFP"},
    {"date": "2026-10-02", "name": "미국 9월 비농업 고용보고서 (NFP)", "impact": "HIGH", "type": "NFP"},
    {"date": "2026-11-06", "name": "미국 10월 비농업 고용보고서 (NFP)", "impact": "HIGH", "type": "NFP"},
    {"date": "2026-12-04", "name": "미국 11월 비농업 고용보고서 (NFP)", "impact": "HIGH", "type": "NFP"},
]

class MacroEventHorizon:
    """Calculates macro D-Day countdowns and evaluates portfolio exposure risks."""

    def __init__(self, holdings: List[str] = None):
        self.holdings = holdings or ["VTOL", "MDT", "MRK", "STRC"]

    def get_upcoming_macro_events(self, lookahead_days: int = 21) -> List[Dict[str, Any]]:
        """Returns upcoming macro events within the lookahead window."""
        today = datetime.now().date()
        upcoming = []

        for ev in MACRO_CALENDAR_2026:
            try:
                ev_date = datetime.strptime(ev["date"], "%Y-%m-%d").date()
                diff = (ev_date - today).days
                if 0 <= diff <= lookahead_days:
                    d_day_str = "D-DAY (오늘!)" if diff == 0 else f"D-{diff}" if diff > 0 else f"D+{abs(diff)}"
                    upcoming.append({
                        "name": ev["name"],
                        "date": ev["date"],
                        "days_left": diff,
                        "d_day": d_day_str,
                        "impact": ev["impact"],
                        "type": ev["type"]
                    })
            except Exception as e:
                logger.debug("Error parsing macro date: {}", e)

        return sorted(upcoming, key=lambda x: x["days_left"])

    def get_holding_earnings_dates(self, symbols: List[str] = None) -> List[Dict[str, Any]]:
        """Queries estimated earnings dates for current portfolio holdings."""
        syms = symbols or self.holdings
        today = datetime.now().date()
        earnings_list = []

        # Fallback dictionary for known earnings schedules to guarantee zero API delay
        static_earnings_estimates = {
            "VTOL": "2026-11-04",
            "MDT": "2026-08-20",
            "MRK": "2026-10-27",
            "STRC": "2026-11-12",
            "NVDA": "2026-08-26",
            "AAPL": "2026-10-29",
            "MSFT": "2026-10-22",
            "TSLA": "2026-10-21"
        }

        for sym in syms:
            sym_upper = sym.upper()
            earn_date_str = static_earnings_estimates.get(sym_upper, "")
            
            # Try live lookup from yfinance if available
            try:
                import yfinance as yf
                t = yf.Ticker(sym_upper)
                cal = getattr(t, 'calendar', None)
                if cal is not None and not (hasattr(cal, 'empty') and cal.empty):
                    if isinstance(cal, dict) and 'Earnings Date' in cal and cal['Earnings Date']:
                        ed = cal['Earnings Date'][0]
                        earn_date_str = ed.strftime("%Y-%m-%d") if hasattr(ed, 'strftime') else str(ed)[:10]
            except Exception:
                pass

            if earn_date_str:
                try:
                    earn_date = datetime.strptime(earn_date_str, "%Y-%m-%d").date()
                    diff = (earn_date - today).days
                    if -1 <= diff <= 45:
                        d_day_str = "D-DAY (오늘 실적발표!)" if diff == 0 else f"D-{diff}" if diff > 0 else "발표 완료"
                        earnings_list.append({
                            "symbol": sym_upper,
                            "date": earn_date_str,
                            "days_left": diff,
                            "d_day": d_day_str
                        })
                except Exception:
                    pass

        return sorted(earnings_list, key=lambda x: x["days_left"])

    def evaluate_risk_multiplier(self) -> tuple[float, str]:
        """
        Evaluates risk exposure multiplier based on D-Day proximity to high impact events.
        Returns: (multiplier: float 0.5~1.0, rationale: str)
        """
        upcoming_macro = self.get_upcoming_macro_events(lookahead_days=2)
        for ev in upcoming_macro:
            if ev["days_left"] == 0 and ev["impact"] == "CRITICAL":
                return 0.5, f"🚨 {ev['name']} 당일 (D-0): 신규 진입 비중 50% 긴급 방어 모드 발동"
            elif ev["days_left"] == 0:
                return 0.7, f"⚠️ {ev['name']} 발표 당일 (D-0): 변동성 관리 70% 비중 조절"
            elif ev["days_left"] == 1 and ev["impact"] == "CRITICAL":
                return 0.75, f"⚠️ {ev['name']} 하루 전 (D-1): 사전 리스크 75% 비중 조절"

        # Check holding earnings today
        holding_earnings = self.get_holding_earnings_dates()
        for h in holding_earnings:
            if h["days_left"] == 0:
                return 0.8, f"⚠️ 보유 종목 {h['symbol']} 실적발표 당일: 변동성 보호 비중 제한"

        return 1.0, "🟢 주요 거시 지표 일정 안전권 (정상 100% 매매 가동)"

    def format_telegram_card(self, symbols: List[str] = None) -> str:
        """Formats an executive D-Day radar card for Telegram."""
        macro_events = self.get_upcoming_macro_events(lookahead_days=28)
        earnings_events = self.get_holding_earnings_dates(symbols or self.holdings)
        mult, status_msg = self.evaluate_risk_multiplier()

        macro_lines = []
        for ev in macro_events[:4]:
            tag = "🚨" if ev["days_left"] <= 1 else "📅"
            macro_lines.append(f"  • {tag} <b>{ev['name']}</b>: <code>{ev['d_day']}</code> ({ev['date'][5:]})")
        macro_str = "\n".join(macro_lines) if macro_lines else "  • 28일 이내 예정된 주요 지표 없음"

        earn_lines = []
        for earn in earnings_events[:4]:
            tag = "⚡" if earn["days_left"] <= 3 else "💼"
            earn_lines.append(f"  • {tag} <b>{earn['symbol']}</b>: <code>{earn['d_day']}</code> ({earn['date']})")
        earn_str = "\n".join(earn_lines) if earn_lines else "  • 보유 종목 실적발표 안전권 (D-Day 없음)"

        card = (
            f"🔮 <b>[매크로 지표 & 보유종목 실적 D-Day 레이더]</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🛡️ <b>실시간 봇 방어 상태</b>:\n"
            f"<b>{status_msg}</b> (베팅 한도: {mult:.0%})\n\n"
            f"🏛️ <b>미국 주요 경제지표 D-Day</b>:\n{macro_str}\n\n"
            f"📊 <b>보유종목 실적발표(Earnings) D-Day</b>:\n{earn_str}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💡 <i>고위험 지표 당일에는 봇이 자동으로 진입 비중을 축소하여 계좌를 안전하게 보호합니다.</i>"
        )
        return card

if __name__ == "__main__":
    meh = MacroEventHorizon()
    print(meh.format_telegram_card())
