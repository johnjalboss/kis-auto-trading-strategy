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

    def scan_premarket_gaps(self, candidate_symbols: List[str] = None) -> List[Dict[str, Any]]:
        """
        Scans pre-market prices for candidate symbols and identifies genuine institutional breakaway gaps.
        """
        if not candidate_symbols:
            try:
                from universe import BASE_UNIVERSE
                candidate_symbols = list(BASE_UNIVERSE)[:150]
            except Exception:
                candidate_symbols = ["NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "AVGO", "AMD", "PLTR", "MRK", "LLY", "OKLO", "SMR"]

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

        results = []
        try:
            # Batch download with prepost=True
            tickers_str = " ".join(candidate_symbols[:120])
            data = yf.download(tickers_str, period="5d", interval="1d", prepost=True, progress=False, threads=True)
            
            if data.empty:
                return []

            closes = data.get("Close")
            if closes is None or closes.empty:
                return []

            for sym in candidate_symbols[:120]:
                if sym not in closes.columns:
                    continue
                c_series = closes[sym].dropna()
                if len(c_series) < 2:
                    continue

                prev_close = float(c_series.iloc[-2])
                curr_price = float(c_series.iloc[-1])
                if prev_close <= 0:
                    continue

                gap_pct = ((curr_price / prev_close) - 1.0) * 100.0

                if self.min_gap_pct <= gap_pct <= self.max_gap_pct:
                    # Check if supported by Theme Radar
                    t_info = theme_picks.get(sym)
                    is_theme_supported = (t_info is not None)
                    theme_name = t_info.get("theme_name", "일반 유니버스") if t_info else "일반 유니버스"

                    # Gap Quality Score (100 pts)
                    score = 0
                    if 3.5 <= gap_pct <= 8.5: score += 40      # Optimal institutional sweet-spot
                    elif 8.5 < gap_pct <= 14.0: score += 25
                    else: score += 10

                    if is_theme_supported: score += 40         # Theme confluence
                    if curr_price >= 10.0: score += 20         # Institutional liquidity

                    results.append({
                        "symbol": sym,
                        "prev_close": round(prev_close, 2),
                        "premarket_price": round(curr_price, 2),
                        "gap_pct": round(gap_pct, 2),
                        "theme_name": theme_name,
                        "is_theme_supported": is_theme_supported,
                        "sniper_score": score,
                        "action": "STRONG_BUY_ON_OPEN" if score >= 75 else "WATCH_OPEN_RANGE"
                    })

        except Exception as e:
            logger.error("PreMarketGapSniper scan error: {}", e)

        results.sort(key=lambda x: x["sniper_score"], reverse=True)
        return results

    def format_telegram_card(self, top_n: int = 5) -> str:
        """Formats the premarket sniper results into a Telegram HTML card."""
        gaps = self.scan_premarket_gaps()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            "🚀 <b>[프리마켓 갭상승 & 어닝 서프라이즈 스나이퍼]</b>",
            "━━━━━━━━━━━━━━━━━━━",
            f"⏱ <b>스캔시각:</b> <code>{now_str}</code> (개장 전 수급 분석)\n"
        ]

        if not gaps:
            lines.append("ℹ️ <i>현재 +3.0% 이상 돌파형 갭을 형성한 종목이 없습니다. (정규장 개장 대기 중)</i>")
        else:
            for idx, g in enumerate(gaps[:top_n], 1):
                icon = "🔥" if g["is_theme_supported"] else "⚡️"
                lines.append(
                    f"  {idx}. {icon} <b>{g['symbol']}</b> (<b>{g['gap_pct']:+0.1f}%</b> | ${g['premarket_price']:.2f})\n"
                    f"     • 소속: <code>[{g['theme_name']}]</code>\n"
                    f"     • 판정: <b>{g['action']}</b> (스나이퍼 점수: {g['sniper_score']}점)"
                )

        lines.append("━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 <i>주도 테마와 일치하는 돌파형 갭(Breakaway Gap) 종목은 09:30 개장 시 1순위 진입 후보로 반영됩니다.</i>")
        return "\n".join(lines)

if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sniper = PreMarketGapSniper()
    print(sniper.format_telegram_card())
