"""
1. Mark Minervini Volatility Contraction Pattern (VCP) Breakout Engine (vcp_breakout_engine.py)
================================================================================================
Theoretical Foundation (Mark Minervini / US Investing Champion & Stan Weinstein Stage 2):
- A valid VCP exhibits 2 to 4 successive contractions in price depth:
    Wave 1 depth (e.g. 10% ~ 20%) -> Wave 2 depth (e.g. 5% ~ 10%) -> Wave 3 depth (e.g. 2% ~ 5%).
- Volume dries up significantly during contractions (institutional absorption/dry-up).
- The final Pivot Breakout occurs when price pierces resistance with Volume Ratio >= 1.4x the 20-day average.
- Awards +20 points for high-conviction VCP Pivot Breakouts.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from loguru import logger

class VCPBreakoutEngine:
    """Detects Volatility Contraction Patterns (VCP) & Pivot Point Breakouts"""

    def analyze(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        res = {
            "symbol": symbol,
            "is_vcp_pattern": False,
            "is_pivot_breakout": False,
            "contractions_count": 0,
            "final_contraction_depth_pct": 0.0,
            "pivot_resistance": 0.0,
            "score_bonus": 0,
            "label": "NORMAL_STRUCTURE"
        }

        if df is None or len(df) < 30 or 'Close' not in df.columns or 'High' not in df.columns:
            return res

        try:
            close = df['Close'].values
            high = df['High'].values
            low = df['Low'].values
            volume = df['Volume'].values if 'Volume' in df.columns else np.ones(len(close))

            # Lookback 30-day window
            w_high = high[-30:]
            w_low = low[-30:]
            w_close = close[-30:]
            w_vol = volume[-30:]

            # Divide 30-day window into 3 consecutive 10-day segments to measure wave depth
            seg1_depth = ((np.max(w_high[:10]) - np.min(w_low[:10])) / np.max(w_high[:10])) * 100.0
            seg2_depth = ((np.max(w_high[10:20]) - np.min(w_low[10:20])) / np.max(w_high[10:20])) * 100.0
            seg3_depth = ((np.max(w_high[20:]) - np.min(w_low[20:])) / np.max(w_high[20:])) * 100.0

            res["final_contraction_depth_pct"] = round(seg3_depth, 2)

            # VCP Condition: Progressive narrowing of wave amplitudes (seg1 > seg2 > seg3 or seg2 > seg3 with tight base)
            is_contracting = (seg1_depth >= seg2_depth * 0.9 and seg2_depth > seg3_depth) or (seg3_depth <= 4.5 and seg2_depth <= 9.0)

            if is_contracting:
                res["is_vcp_pattern"] = True
                res["contractions_count"] = 3 if seg1_depth > seg2_depth > seg3_depth else 2
                res["label"] = "VCP_CONTRACTION_FORMED"

                # Pivot resistance = highest high of the last 15 days
                pivot_price = float(np.max(w_high[15:-1])) if len(w_high) >= 16 else float(np.max(w_high[:-1]))
                res["pivot_resistance"] = round(pivot_price, 2)

                curr_p = float(close[-1])
                curr_v = float(volume[-1])
                avg_v = float(np.mean(w_vol[-20:-1])) if len(w_vol) >= 21 else float(np.mean(w_vol))
                vol_ratio = curr_v / avg_v if avg_v > 0 else 1.0

                # Check if current price is breaking out above pivot with volume surge >= 1.35x
                if curr_p >= pivot_price * 0.998 and vol_ratio >= 1.35:
                    res["is_pivot_breakout"] = True
                    res["score_bonus"] = 20
                    res["label"] = "VCP_PIVOT_BREAKOUT"
                    logger.info("📈 [VCP_BREAKOUT] {} confirmed Minervini VCP Pivot Breakout (Pivot=${:.2f}, FinalDepth={:.1f}%, RVOL={:.2f}) -> +20 pts",
                                symbol, pivot_price, seg3_depth, vol_ratio)
                elif is_contracting and seg3_depth <= 3.5:
                    res["score_bonus"] = 10
                    res["label"] = "VCP_TIGHT_COIL_BASE"

            return res

        except Exception as e:
            logger.debug("VCP analysis failed for {}: {}", symbol, e)
            return res
