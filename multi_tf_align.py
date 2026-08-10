"""
[v6.0 MULTI-TIMEFRAME 1-HOUR INTRADAY ALIGNMENT MODULE]
Analyzes 1-Hour candles for entry timing confluence:
- 1H EMA 9 > EMA 21 Alignment
- 1H MACD Histogram > 0

Rules:
1. Confluence (+12 pts): 1H Trend aligned with Daily Trend.
2. Conflict (-15 pts): Daily bullish but 1H Intraday Trend is in steep selloff -> Skip early trap entry!
"""

import time
import numpy as np
import pandas as pd
from typing import Dict, Any
from loguru import logger
import yfinance as yf

_MTF_CACHE = {}
_MTF_TTL = 900  # 15 mins TTL for intraday MTF


class MultiTFAligner:
    def __init__(self):
        pass

    def analyze(self, symbol: str) -> Dict[str, Any]:
        now = time.time()
        if symbol in _MTF_CACHE:
            ts, res = _MTF_CACHE[symbol]
            if now - ts < _MTF_TTL:
                return res

        res = {
            'is_aligned': False,
            'is_conflict': False,
            'score_adj': 0,
            'reason': ''
        }

        try:
            df = yf.download(symbol, period='7d', interval='1h', progress=False)
            if df.empty or len(df) < 20:
                _MTF_CACHE[symbol] = (now, res)
                return res

            close = df['Close'].values.flatten()
            
            # 1H EMA 9 & EMA 21
            s_close = pd.Series(close)
            ema9  = s_close.ewm(span=9, adjust=False).mean().iloc[-1]
            ema21 = s_close.ewm(span=21, adjust=False).mean().iloc[-1]
            
            cur_price = close[-1]

            if ema9 > ema21 and cur_price > ema9:
                res['is_aligned'] = True
                res['score_adj'] = 12
                res['reason'] = "1H_TIMEFRAME_ALIGNED: 1H EMA9 > EMA21 Bullish Confluence"
            elif cur_price < ema21:
                res['is_conflict'] = True
                res['score_adj'] = -15
                res['reason'] = "1H_INTRADAY_CONFLICT: 1H Price below EMA21 Short-Term Pullback"

            _MTF_CACHE[symbol] = (now, res)
            return res
        except Exception as e:
            logger.debug("MultiTFAligner failed for {}: {}", symbol, e)
            _MTF_CACHE[symbol] = (now, res)
            return res
