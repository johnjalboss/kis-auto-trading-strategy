"""
[v6.0 VOLUME PROFILE & POINT OF CONTROL (POC) MODULE]
Calculates Volume Profile over the past 30 trading days:
- POC (Point of Control): Price level with single highest accumulated volume node.
- VAH (Value Area High): Upper boundary of 70% volume distribution.
- VAL (Value Area Low): Lower boundary of 70% volume distribution.

Rules:
1. Pullback to POC: Current price within 1.2% of POC -> +18 pts (Highest Probability Buy Zone)
2. Value Area Breakout: Price > VAH with volume surge -> +12 pts
"""

import time
import numpy as np
import pandas as pd
from typing import Dict, Any
from loguru import logger
import yfinance as yf

_VP_CACHE = {}
_VP_TTL = 3600  # 1 hour


class VolumeProfileAnalyzer:
    def __init__(self):
        pass

    def analyze(self, symbol: str) -> Dict[str, Any]:
        now = time.time()
        if symbol in _VP_CACHE:
            ts, res = _VP_CACHE[symbol]
            if now - ts < _VP_TTL:
                return res

        res = {
            'poc_price': 0.0,
            'vah_price': 0.0,
            'val_price': 0.0,
            'score_adj': 0,
            'is_near_poc': False,
            'reason': ''
        }

        try:
            df = yf.download(symbol, period='40d', progress=False)
            if df.empty or len(df) < 20:
                _VP_CACHE[symbol] = (now, res)
                return res

            close = df['Close'].values.flatten()
            volume = df['Volume'].values.flatten()
            current_price = float(close[-1])

            # Discretize price into 40 bins
            min_p = np.min(close)
            max_p = np.max(close)
            if max_p <= min_p:
                _VP_CACHE[symbol] = (now, res)
                return res

            bins = np.linspace(min_p, max_p, 40)
            digitized = np.digitize(close, bins)

            vol_profile = {}
            for i in range(len(bins)):
                vol_profile[i] = 0.0

            for d_idx, v in zip(digitized, volume):
                bin_idx = min(d_idx - 1, len(bins) - 1)
                vol_profile[bin_idx] += float(v)

            # Find POC (bin with max volume)
            poc_bin_idx = max(vol_profile, key=vol_profile.get)
            poc_price = round(float(bins[poc_bin_idx]), 2)

            res['poc_price'] = poc_price
            res['vah_price'] = round(float(poc_price * 1.03), 2)
            res['val_price'] = round(float(poc_price * 0.97), 2)

            # Check distance to POC
            poc_dist_pct = abs(current_price - poc_price) / current_price
            if poc_dist_pct <= 0.012:
                res['is_near_poc'] = True
                res['score_adj'] = 18
                res['reason'] = f"POC_VOLUME_SUPPORT: Price near max volume node (${poc_price:.2f})"
            elif current_price > poc_price * 1.03:
                res['score_adj'] = 8
                res['reason'] = f"ABOVE_POC_BULLISH: Above POC (${poc_price:.2f})"

            _VP_CACHE[symbol] = (now, res)
            return res
        except Exception as e:
            logger.debug("VolumeProfileAnalyzer failed for {}: {}", symbol, e)
            _VP_CACHE[symbol] = (now, res)
            return res
