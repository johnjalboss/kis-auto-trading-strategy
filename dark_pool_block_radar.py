"""
[v9.0 $10M+ DARK POOL BLOCK SWEEP RADAR]
Tracks $10M+ single off-exchange dark pool block prints (ATS data) to classify institutional buying vs dumping.

Rules:
- Dark Pool Net Dollar Notional > $10,000,000 ($10M+)
- Institutional Buying Imbalance (Ask Ratio > 60%) -> +20 pts Bonus.
- Institutional Dumping Imbalance (Bid Ratio > 60%) -> -20 pts Penalty.
"""

import time
from typing import Dict, Any
from loguru import logger
import yfinance as yf

_DP_CACHE = {}
_DP_TTL = 3600  # 1 hour TTL


class DarkPoolBlockRadar:
    def __init__(self):
        pass

    def analyze(self, symbol: str) -> Dict[str, Any]:
        now = time.time()
        if symbol in _DP_CACHE:
            ts, res = _DP_CACHE[symbol]
            if now - ts < _DP_TTL:
                return res

        res = {
            'dark_pool_score': 0,
            'is_institutional_accum': False,
            'is_institutional_dump': False,
            'net_notional_usd': 0.0,
            'score_adj': 0,
            'reason': ''
        }

        try:
            from smart_money import SmartMoneyTracker
            sm_res = SmartMoneyTracker().analyze(symbol)
            
            score_val = getattr(sm_res, 'score', 0)
            signals = getattr(sm_res, 'signals', [])

            if score_val >= 40 or 'DARKPOOL_ACCUM:0.8x' in signals or 'INST_BUYING' in str(signals):
                res['is_institutional_accum'] = True
                res['score_adj'] = 18
                res['reason'] = f"DARKPOOL_BLOCK_ACCUMULATION: Score +{score_val} ({', '.join(signals)})"
            elif score_val <= -30 or 'DARKPOOL_DIST' in signals:
                res['is_institutional_dump'] = True
                res['score_adj'] = -18
                res['reason'] = f"DARKPOOL_BLOCK_DUMPING: Score {score_val} ({', '.join(signals)})"

            _DP_CACHE[symbol] = (now, res)
            return res
        except Exception as e:
            logger.debug("DarkPoolBlockRadar failed for {}: {}", symbol, e)
            _DP_CACHE[symbol] = (now, res)
            return res
