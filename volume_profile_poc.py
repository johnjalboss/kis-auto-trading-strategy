"""
1. Volume Profile POC Support Bounce Engine (volume_profile_poc.py)
===================================================================
Concept (Market Profile & Auction Market Theory):
- Computes the Point of Control (POC) — price level where the most volume was traded over the last 60 days.
- Computes Value Area (70% of total volume distribution): Value Area High (VAH) and Value Area Low (VAL).
- If the current price pulls back to the POC level (within +0.0% to +2.5%) and starts bouncing with expanding volume,
  it represents strong institutional accumulation support.
- Awards +15 points for high-conviction Volume Profile POC Support Bounce.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from loguru import logger

class VolumeProfilePOCEngine:
    """Calculates Volume Profile Point of Control (POC) & Support Bounces"""

    def __init__(self, bins: int = 50, lookback_days: int = 60):
        self.bins = bins
        self.lookback_days = lookback_days

    def analyze(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        Analyze 60-day volume profile and test for POC support bounce
        """
        res = {
            "symbol": symbol,
            "poc_price": 0.0,
            "vah_price": 0.0,
            "val_price": 0.0,
            "is_poc_bounce": False,
            "dist_from_poc_pct": 0.0,
            "score_bonus": 0,
            "label": "NORMAL_PROFILE"
        }

        if df is None or len(df) < 20 or 'Volume' not in df.columns:
            return res

        try:
            df_recent = df.tail(self.lookback_days)
            close = df_recent['Close'].values
            volume = df_recent['Volume'].values
            cur_p = float(close[-1])

            if cur_p <= 0 or np.sum(volume) <= 0:
                return res

            price_min = np.min(df_recent['Low'].values) if 'Low' in df_recent.columns else np.min(close)
            price_max = np.max(df_recent['High'].values) if 'High' in df_recent.columns else np.max(close)

            if price_max <= price_min:
                return res

            # Build histogram bins of volume by price
            bin_edges = np.linspace(price_min, price_max, self.bins + 1)
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0
            vol_profile = np.zeros(self.bins)

            for i in range(len(close)):
                p = close[i]
                v = volume[i]
                idx = np.digitize(p, bin_edges) - 1
                idx = np.clip(idx, 0, self.bins - 1)
                vol_profile[idx] += v

            # Point of Control (POC) = bin with max volume
            poc_idx = np.argmax(vol_profile)
            poc_price = float(bin_centers[poc_idx])

            # Value Area: 70% of total volume surrounding POC
            total_vol = np.sum(vol_profile)
            target_va_vol = total_vol * 0.70

            cum_vol = vol_profile[poc_idx]
            left = poc_idx
            right = poc_idx

            while cum_vol < target_va_vol and (left > 0 or right < self.bins - 1):
                next_left_vol = vol_profile[left - 1] if left > 0 else 0
                next_right_vol = vol_profile[right + 1] if right < self.bins - 1 else 0
                if next_left_vol >= next_right_vol and left > 0:
                    left -= 1
                    cum_vol += vol_profile[left]
                elif right < self.bins - 1:
                    right += 1
                    cum_vol += vol_profile[right]
                else:
                    break

            val_price = float(bin_centers[left])
            vah_price = float(bin_centers[right])

            dist_from_poc = ((cur_p - poc_price) / poc_price) * 100.0
            dist_from_vah = ((cur_p - vah_price) / vah_price) * 100.0 if vah_price > 0 else 0.0
            dist_from_val = ((cur_p - val_price) / val_price) * 100.0 if val_price > 0 else 0.0

            res["poc_price"] = round(poc_price, 2)
            res["vah_price"] = round(vah_price, 2)
            res["val_price"] = round(val_price, 2)
            res["dist_from_poc_pct"] = round(dist_from_poc, 2)
            res["dist_from_vah_pct"] = round(dist_from_vah, 2)
            res["dist_from_val_pct"] = round(dist_from_val, 2)

            # 1. POC Support Bounce (0.0% to +2.5% above POC with positive 3-day momentum)
            if 0.0 <= dist_from_poc <= 2.5 and len(close) >= 4 and close[-1] > close[-3]:
                res["is_poc_bounce"] = True
                res["score_bonus"] = 15
                res["label"] = "POC_SUPPORT_BOUNCE"
                logger.info("📈 [VOLUME_PROFILE_POC] {} is bouncing off 60-day POC level ${:.2f} (+{:.1f}%) -> +15 pts",
                            symbol, poc_price, dist_from_poc)

            # 2. VAH Value Expansion Markup Breakout (0.0% to +3.5% above VAH with volume surge)
            elif 0.0 <= dist_from_vah <= 3.5 and len(close) >= 4 and close[-1] >= close[-2]:
                vol_recent_avg = np.mean(volume[-5:]) if len(volume) >= 5 else 1.0
                vol_prior_avg = np.mean(volume[-20:-5]) if len(volume) >= 20 else vol_recent_avg
                vol_ratio = vol_recent_avg / max(vol_prior_avg, 1.0)
                bonus = 15 if vol_ratio >= 1.25 else 10
                res["score_bonus"] = bonus
                res["label"] = "VAH_VALUE_EXPANSION_BREAKOUT"
                logger.info("🚀 [VOLUME_PROFILE_POC] {} breaking above Value Area High ${:.2f} (Dist: +{:.1f}%, VolRatio: {:.2f}x) -> +{} pts",
                            symbol, vah_price, dist_from_vah, vol_ratio, bonus)

            # 3. VAL Mean-Reversion Value Bounce (0.0% to +2.0% above VAL)
            elif 0.0 <= dist_from_val <= 2.0 and len(close) >= 4 and close[-1] > close[-2]:
                res["score_bonus"] = 10
                res["label"] = "VAL_SUPPORT_BOUNCE"
                logger.info("🛡️ [VOLUME_PROFILE_POC] {} bouncing off Value Area Low ${:.2f} (+{:.1f}%) -> +10 pts",
                            symbol, val_price, dist_from_val)

            elif cur_p > vah_price:
                res["score_bonus"] = 5
                res["label"] = "ABOVE_VALUE_AREA_EXPANSION"
            elif cur_p < val_price:
                res["score_bonus"] = -10
                res["label"] = "BELOW_VALUE_AREA_DISTRIBUTION"

            return res

        except Exception as e:
            logger.debug("Volume profile POC analysis failed for {}: {}", symbol, e)
            return res
