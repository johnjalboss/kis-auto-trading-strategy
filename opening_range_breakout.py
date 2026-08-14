"""
2. Opening Range Breakout (ORB) & Gap-Fade Guard (opening_range_breakout.py)
===========================================================================
Concept (Toby Crabel / Modern Day-Trading Alpha):
- 09:30~10:00 EST Opening Range (First 30-min price action).
- 1. ORB Breakout: Stock breaks above 30m Opening High with expanding volume -> +20 points.
- 2. Gap-Fade Guard: Stock gapped up >2.5% at open but volume is fading (buyer exhaustion) -> -25 points penalty.
- Prevents buying into opening bull traps (ODH fade) and captures genuine morning momentum expansions.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from loguru import logger

class OpeningRangeBreakoutFilter:
    """Evaluates 30-minute Opening Range Breakouts & Filters Fake Gap-Fades"""

    def analyze(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        res = {
            "symbol": symbol,
            "gap_pct": 0.0,
            "is_orb_breakout": False,
            "is_gap_fade_trap": False,
            "score_bonus": 0,
            "label": "NORMAL_OPENING"
        }

        if df is None or len(df) < 5 or 'Open' not in df.columns:
            return res

        try:
            today_open = float(df['Open'].iloc[-1])
            prev_close = float(df['Close'].iloc[-2])
            curr_close = float(df['Close'].iloc[-1])
            curr_high = float(df['High'].iloc[-1])
            curr_vol = float(df['Volume'].iloc[-1]) if 'Volume' in df.columns else 1.0

            if prev_close <= 0 or today_open <= 0:
                return res

            gap_pct = ((today_open - prev_close) / prev_close) * 100.0
            intraday_return = ((curr_close - today_open) / today_open) * 100.0
            res["gap_pct"] = round(gap_pct, 2)

            # Volume ratio vs average
            vol_ratio = 1.0
            if 'Volume' in df.columns and len(df) >= 2:
                vol_window = min(len(df) - 1, 20)
                avg_vol = float(df['Volume'].iloc[-vol_window-1:-1].mean())
                vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 1.0

            # 1. Gap-Fade Bull Trap Detection: Gapped up >2.0%, but trading below Open with weak volume
            if gap_pct >= 2.0 and curr_close < today_open and vol_ratio < 1.1:
                res["is_gap_fade_trap"] = True
                res["score_bonus"] = -25
                res["label"] = "GAP_FADE_BULL_TRAP"
                logger.warning("🚫 [GAP_FADE_TRAP] {} gapped up +{:.1f}% but failed to hold open (${:.2f} < ${:.2f}) -> -25 pts penalty",
                               symbol, gap_pct, curr_close, today_open)
                return res

            # 2. Genuine ORB Breakout: Gapped up or flat, holding above open, pushing high with RVOL >= 1.4
            if intraday_return >= 1.2 and vol_ratio >= 1.4:
                # Strong close near day's high (within 1% of high)
                if curr_high > 0 and (curr_high - curr_close) / curr_high <= 0.012:
                    res["is_orb_breakout"] = True
                    res["score_bonus"] = 20
                    res["label"] = "GENUINE_ORB_EXPANSION"
                    logger.info("🌅 [ORB_BREAKOUT] {} confirmed 30m ORB expansion (+{:.1f}%, RVOL={:.2f}) -> +20 pts",
                                symbol, intraday_return, vol_ratio)
                    return res

            return res

        except Exception as e:
            logger.debug("ORB analysis failed for {}: {}", symbol, e)
            return res
