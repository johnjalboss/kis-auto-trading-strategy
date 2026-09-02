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

import calendar

def get_dynamic_macro_calendar(start_date: date, months_ahead: int = 4) -> List[Dict[str, Any]]:
    """
    Calculates statutory US economic release schedules dynamically using calendar mathematics:
    1. ISM Manufacturing PMI (1st business day) & Services PMI (3rd business day)
    2. Non-Farm Payrolls (NFP) & Unemployment (1st Friday)
    3. CPI Consumer Price Index (2nd Wednesday) & PPI Producer Price Index (2nd Thursday)
    4. FOMC Rate Decision (3rd Wednesday of scheduled months) & FOMC Minutes
    5. Monthly OpEx & Quadruple Witching Gamma Pin (3rd Friday)
    6. Advance / Prelim / Final GDP (Last Thursday)
    7. Core PCE Price Index (Last Friday - Fed's #1 Favorite Inflation Target)
    """
    events = []
    y = start_date.year
    m = start_date.month

    for _ in range(months_ahead):
        cal = calendar.monthcalendar(y, m)
        prev_m = m - 1 if m > 1 else 12
        
        # 1. ISM Manufacturing PMI (1st business day)
        ism_mfg_day = 1
        while date(y, m, ism_mfg_day).weekday() >= 5:
            ism_mfg_day += 1
        events.append({
            "date": date(y, m, ism_mfg_day).strftime("%Y-%m-%d"),
            "name": f"미국 {prev_m}월 ISM 제조업 PMI",
            "impact": "MEDIUM",
            "type": "PMI"
        })

        # 2. ADP Non-Farm Employment (First Wednesday) & JOLTS Job Openings
        wednesdays = [week[2] for week in cal if week[2] != 0]
        first_wed = wednesdays[0]
        events.append({
            "date": date(y, m, first_wed).strftime("%Y-%m-%d"),
            "name": f"미국 {prev_m}월 ADP 민간 비농업 고용보고서",
            "impact": "HIGH",
            "type": "ADP_NFP"
        })
        events.append({
            "date": date(y, m, first_wed).strftime("%Y-%m-%d"),
            "name": f"미국 {prev_m}월 JOLTS 구인·이직 보고서 (구인건수)",
            "impact": "HIGH",
            "type": "JOLTS"
        })

        # 3. ISM Services PMI (3rd business day)
        biz_days = [d for d in range(1, 32) if d <= calendar.monthrange(y, m)[1] and date(y, m, d).weekday() < 5]
        ism_svc_day = biz_days[2] if len(biz_days) >= 3 else biz_days[-1]
        events.append({
            "date": date(y, m, ism_svc_day).strftime("%Y-%m-%d"),
            "name": f"미국 {prev_m}월 ISM 서비스업 PMI",
            "impact": "MEDIUM",
            "type": "PMI"
        })

        # 4. Official Non-Farm Payrolls (NFP) & Unemployment: First Friday of each month (BLS)
        fridays = [week[4] for week in cal if week[4] != 0]
        first_fri = fridays[0]
        nfp_date = date(y, m, first_fri)
        events.append({
            "date": nfp_date.strftime("%Y-%m-%d"),
            "name": f"미국 {prev_m}월 노동부 공식 비농업 고용보고서 (NFP) & 실업률",
            "impact": "CRITICAL",
            "type": "NFP"
        })

        # 5. CPI: Second Wednesday of each month
        second_wed = wednesdays[1] if len(wednesdays) > 1 else wednesdays[0]
        cpi_date = date(y, m, second_wed)
        events.append({
            "date": cpi_date.strftime("%Y-%m-%d"),
            "name": f"미국 {prev_m}월 CPI (소비자물가지수)",
            "impact": "CRITICAL",
            "type": "CPI"
        })

        # 6. PPI & Retail Sales (2nd Thursday / mid-month)
        thursdays = [week[3] for week in cal if week[3] != 0]
        second_thu = thursdays[1] if len(thursdays) > 1 else thursdays[0]
        events.append({
            "date": date(y, m, second_thu).strftime("%Y-%m-%d"),
            "name": f"미국 {prev_m}월 PPI (생산자물가지수) & 소매판매",
            "impact": "HIGH",
            "type": "PPI"
        })

        # 7. UMich Consumer Sentiment (2nd Friday & Final 4th Friday)
        second_fri = fridays[1] if len(fridays) > 1 else fridays[0]
        events.append({
            "date": date(y, m, second_fri).strftime("%Y-%m-%d"),
            "name": f"미국 {m}월 미시간대 소비자심리지수 (예비치)",
            "impact": "MEDIUM",
            "type": "SENTIMENT"
        })

        # 8. Weekly Initial Jobless Claims (Every Thursday in the month)
        for thu_day in thursdays:
            events.append({
                "date": date(y, m, thu_day).strftime("%Y-%m-%d"),
                "name": f"미국 주간 신규 실업수당 청구건수 (Jobless Claims)",
                "impact": "MEDIUM",
                "type": "CLAIMS"
            })

        # 9. FOMC Rate Decision (Jan, Mar, May, Jun, Jul, Sep, Nov, Dec - 3rd Wednesday)
        if m in [1, 3, 5, 6, 7, 9, 11, 12]:
            third_wed = wednesdays[2] if len(wednesdays) > 2 else wednesdays[-1]
            fomc_date = date(y, m, third_wed)
            events.append({
                "date": fomc_date.strftime("%Y-%m-%d"),
                "name": f"FOMC 연준 기준금리 결정 ({y}년 {m}월)",
                "impact": "CRITICAL",
                "type": "FOMC"
            })

        # 10. Monthly Options Expiration (OpEx / Gamma Pin): 3rd Friday of every month
        third_fri = fridays[2] if len(fridays) > 2 else fridays[-1]
        is_quad = m in [3, 6, 9, 12]
        opex_name = f"미국 {m}월 쿼드러플 위칭데이 (선물옵션 동시만기)" if is_quad else f"미국 {m}월 월간 옵션 만기일 (OpEx)"
        events.append({
            "date": date(y, m, third_fri).strftime("%Y-%m-%d"),
            "name": opex_name,
            "impact": "HIGH" if is_quad else "MEDIUM",
            "type": "OPEX"
        })

        # 11. GDP Growth Rate (Last Thursday of the month)
        last_thu = thursdays[-1]
        events.append({
            "date": date(y, m, last_thu).strftime("%Y-%m-%d"),
            "name": f"미국 분기 GDP 성장률 발표 ({m}월)",
            "impact": "HIGH",
            "type": "GDP"
        })

        # 12. Core PCE Price Index (Last Friday of the month - Fed's #1 Favorite Gauge)
        last_fri = fridays[-1]
        events.append({
            "date": date(y, m, last_fri).strftime("%Y-%m-%d"),
            "name": f"미국 {prev_m}월 근원 PCE 물가지수 (연준 최선호)",
            "impact": "CRITICAL",
            "type": "PCE"
        })

        m += 1
        if m > 12:
            m = 1
            y += 1

    return sorted(events, key=lambda x: x["date"])


class MacroEventHorizon:
    """Calculates macro D-Day countdowns and evaluates portfolio exposure risks."""

    def __init__(self, holdings: List[str] = None):
        if holdings:
            self.holdings = holdings
        else:
            try:
                from trader import Trader
                pos = Trader().get_positions()
                self.holdings = [p.symbol for p in pos] if pos else []
            except Exception:
                self.holdings = []

    def get_upcoming_macro_events(self, lookahead_days: int = 21) -> List[Dict[str, Any]]:
        """Returns upcoming macro events within the lookahead window."""
        try:
            import pytz
            today = datetime.now(pytz.timezone('America/New_York')).date()
        except Exception:
            today = datetime.utcnow().date()

        macro_events = get_dynamic_macro_calendar(today, months_ahead=3)
        upcoming = []

        for ev in macro_events:
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
        if symbols is not None:
            syms = symbols
        elif self.holdings:
            syms = self.holdings
        else:
            syms = ["NVDA", "AAPL", "MSFT", "TSLA"]

        try:
            import pytz
            today = datetime.now(pytz.timezone('America/New_York')).date()
        except Exception:
            today = datetime.utcnow().date()

        earnings_list = []

        for sym in syms:
            sym_upper = sym.upper()
            earn_date_str = ""
            
            # Live lookup from yfinance
            try:
                import yfinance as yf
                import pandas as pd
                t = yf.Ticker(sym_upper)
                
                # Method 1: ticker.calendar
                cal = getattr(t, 'calendar', None)
                if cal is not None:
                    if isinstance(cal, dict):
                        ed = cal.get('Earnings Date', [])
                        if ed:
                            first_ed = ed[0] if isinstance(ed, (list, tuple)) else ed
                            earn_date_str = first_ed.strftime("%Y-%m-%d") if hasattr(first_ed, 'strftime') else str(first_ed)[:10]
                    elif hasattr(cal, 'loc') and 'Earnings Date' in cal.index:
                        ed_series = cal.loc['Earnings Date']
                        if not ed_series.empty:
                            first_ed = ed_series.iloc[0]
                            earn_date_str = first_ed.strftime("%Y-%m-%d") if hasattr(first_ed, 'strftime') else str(first_ed)[:10]

                # Method 2: ticker.earnings_dates
                if not earn_date_str:
                    edates = getattr(t, 'earnings_dates', None)
                    if edates is not None and not edates.empty:
                        now_dt = pd.to_datetime(today)
                        future_ed = edates[edates.index >= now_dt]
                        if not future_ed.empty:
                            next_dt = future_ed.index[-1]
                            earn_date_str = next_dt.strftime("%Y-%m-%d")
                        else:
                            earn_date_str = edates.index[0].strftime("%Y-%m-%d")

                # Method 3: info earnings timestamp
                if not earn_date_str:
                    info = getattr(t, 'info', {}) or {}
                    ts = info.get('earningsTimestamp') or info.get('earningsTimestampStart')
                    if ts and float(ts) > 0:
                        earn_date_str = datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d")

            except Exception as e:
                logger.debug("Earnings live fetch error for {}: {}", sym_upper, e)

            if earn_date_str:
                try:
                    earn_date = datetime.strptime(earn_date_str, "%Y-%m-%d").date()
                    diff = (earn_date - today).days
                    if -3 <= diff <= 90:
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
        for ev in macro_events[:6]:
            tag = "🚨" if ev["days_left"] <= 1 or ev["impact"] == "CRITICAL" else ("🔥" if ev["impact"] == "HIGH" else "📅")
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
            f"📖 <b>[D-Day 레이더 초보자 3초 이해 가이드]</b>\n"
            f"• <b>D-Day가 D-0, D-1</b>인 빨간색(🚨) 주요 지표(FOMC 금리/CPI 물가)가 다가오면, 봇이 스스로 매수 비중을 50~70%로 줄여 깜짝 변동성 충격으로부터 원금을 안전하게 지킵니다.\n"
            f"• <b>보유 종목 실적 발표</b>가 48시간 이내로 다가오면 도박성 갭하락 위험을 막기 위해 신규 진입을 전면 차단합니다."
        )
        return card

if __name__ == "__main__":
    meh = MacroEventHorizon()
    print(meh.format_telegram_card())
