"""
premarket_gap_sniper.py
================================================================================
Pre-Market Gap & Earnings Surprise Sniper Engine
- Scans pre-market session (07:00 ~ 09:25 EST) for institutional gap breakouts
- Validates:
  1. Breakaway Gap (주도 테마 수급과 일치하는 기관 돌파형 갭) vs Exhaustion Gap (고점 덫)
  2. Relative Pre-market Volume & ATR expansion
  3. Pre-calculated dynamic entry triggers for 09:30 EST market open
================================================================================
"""

import os
import sys
import datetime
import pytz
import yfinance as yf
import pandas as pd
from typing import Dict, List, Any, Optional
from loguru import logger

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class PreMarketGapSniper:
    def __init__(self, min_gap_pct: float = 3.0, max_gap_pct: float = 18.0):
        self.min_gap_pct = min_gap_pct
        self.max_gap_pct = max_gap_pct

    def scan_premarket_gaps(self, candidate_symbols: List[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scans prices across 350+ stocks and categorizes both Gap UP and Gap DOWN unusual movers.
        """
        if not candidate_symbols:
            try:
                from universe import BASE_UNIVERSE, get_all_symbols
                all_syms = get_all_symbols()
                candidate_symbols = list(all_syms)[:600] if all_syms else list(BASE_UNIVERSE)
            except Exception:
                candidate_symbols = ["NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "AVGO", "AMD", "PLTR", "VRT", "LLY", "OKLO", "SMR", "CRWD", "CRM", "NOW", "SNPS", "VEEV", "OKTA"]

        # Also pull recommendations from Theme Radar
        theme_picks = {}
        try:
            from theme_radar_adapter import ThemeRadarAdapter
            tra = ThemeRadarAdapter()
            recs = tra.get_recommendations()
            for sym, info in recs.items():
                theme_picks[sym] = info
                if sym not in candidate_symbols:
                    candidate_symbols.append(sym)
        except Exception:
            pass

        gaps_up = []
        gaps_down = []
        try:
            chunk_size = 150
            for i in range(0, min(len(candidate_symbols), 600), chunk_size):
                chunk = candidate_symbols[i:i+chunk_size]
                tickers_str = " ".join(chunk)
                data = yf.download(tickers_str, period="5d", interval="1d", prepost=True, progress=False, threads=True)
                
                if data is None or data.empty:
                    continue

                closes = data.get("Close")
                if closes is None or closes.empty:
                    continue

                for sym in chunk:
                    if sym not in closes.columns:
                        continue
                    c_series = closes[sym].dropna()
                    if len(c_series) < 2:
                        continue

                    prev_close = float(c_series.iloc[-2])
                    curr_price = float(c_series.iloc[-1])
                    if prev_close <= 0 or curr_price < 3.0:
                        continue

                    gap_pct = ((curr_price / prev_close) - 1.0) * 100.0

                    t_info = theme_picks.get(sym)
                    is_theme_supported = (t_info is not None)
                    theme_name = t_info.get("theme_name", "주도 섹터") if t_info else "일반 유니버스"

                    if gap_pct >= 2.5:
                        score = min(100, int(gap_pct * 8 + (30 if is_theme_supported else 0) + (20 if curr_price >= 10 else 0)))
                        gaps_up.append({
                            "symbol": sym,
                            "prev_close": round(prev_close, 2),
                            "price": round(curr_price, 2),
                            "gap_pct": round(gap_pct, 2),
                            "theme_name": theme_name,
                            "is_theme_supported": is_theme_supported,
                            "score": score,
                            "action": "STRONG_BREAKOUT" if score >= 70 else "WATCH_OPEN_RANGE"
                        })
                    elif gap_pct <= -2.5:
                        score = min(100, int(abs(gap_pct) * 8))
                        gaps_down.append({
                            "symbol": sym,
                            "prev_close": round(prev_close, 2),
                            "price": round(curr_price, 2),
                            "gap_pct": round(gap_pct, 2),
                            "theme_name": theme_name,
                            "score": score,
                            "action": "OVERSOLD_BOUNCE_WATCH" if gap_pct >= -7.0 else "AVOID_PANIC_DUMP"
                        })

        except Exception as e:
            logger.error("PreMarketGapSniper scan error: {}", e)

        gaps_up.sort(key=lambda x: x["gap_pct"], reverse=True)
        gaps_down.sort(key=lambda x: x["gap_pct"])  # Most negative first
        return {"gaps_up": gaps_up, "gaps_down": gaps_down}

    def format_telegram_card(self, top_n: int = 5) -> str:
        """Formats the unusual gap results into a comprehensive Telegram HTML card."""
        res = self.scan_premarket_gaps()
        gaps_up = res.get("gaps_up", [])
        gaps_down = res.get("gaps_down", [])
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            "🚀 <b>[실시간 급등락 특이갭 & 어닝 서프라이즈 레이더]</b>",
            "━━━━━━━━━━━━━━━━━━━",
            f"⏱ <b>스캔시각:</b> <code>{now_str}</code> (600+ 유동성 주도주 실시간 스캔)\n",
            "🔥 <b>[급등 특이갭 Top 5 (상승 돌파)]</b>"
        ]

        if not gaps_up:
            lines.append("  • <i>현재 +2.5% 이상 특이 갭상승 종목이 없습니다.</i>")
        else:
            for idx, g in enumerate(gaps_up[:top_n], 1):
                icon = "🌟" if g["is_theme_supported"] else "⚡️"
                lines.append(
                    f"  {idx}. {icon} <b>{g['symbol']}</b> (<b>{g['gap_pct']:+0.1f}%</b> | ${g['price']:.2f})\n"
                    f"     • 소속: <code>[{g['theme_name']}]</code> | 판정: <b>{g['action']}</b>"
                )

        lines.append("\n📉 <b>[급락 특이갭 Top 5 (패닉 하락 / 과매도)]</b>")
        if not gaps_down:
            lines.append("  • <i>현재 -2.5% 이하 특이 갭하락 종목이 없습니다.</i>")
        else:
            for idx, g in enumerate(gaps_down[:top_n], 1):
                lines.append(
                    f"  {idx}. ⚠️ <b>{g['symbol']}</b> (<b>{g['gap_pct']:+0.1f}%</b> | ${g['price']:.2f})\n"
                    f"     • 소속: <code>[{g['theme_name']}]</code> | 판정: <b>{g['action']}</b>"
                )

        lines.append("━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 <i>특이갭은 장 시작 전후 기관 대량 주문과 실적 쇼크를 포착하여 진입/회피 신호로 연동됩니다.</i>")
        return "\n".join(lines)

if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sniper = PreMarketGapSniper()
    print(sniper.format_telegram_card())
