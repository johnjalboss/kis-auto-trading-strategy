"""
[v6.0 INSTITUTIONAL MACRO CROSS-ASSET RISK MATRIX]
Tracks:
1. US 10-Year Treasury Yield (^TNX)
2. US Dollar Index (UUP / DXY)
3. High-Yield Credit Risk Spread (HYG / TLT)

Detects Macro Market Regimes:
- BULL_STABLE: Yields & Dollar stable / falling -> Risk On (+5 pts)
- NEUTRAL: Mixed macro signals -> 0 pts
- HIGH_MACRO_RISK: Yields & Dollar spiking -> Risk Off (-15 pts & raises entry threshold)
"""

import time
import math
from typing import Dict, Any, Tuple
from loguru import logger
import yfinance as yf

_MACRO_CACHE = {}
_MACRO_TTL = 3600  # 1 hour cache


class MacroRiskMatrix:
    def __init__(self):
        pass

    def analyze(self) -> Dict[str, Any]:
        now = time.time()
        if 'cached_result' in _MACRO_CACHE:
            ts, res = _MACRO_CACHE['cached_result']
            if now - ts < _MACRO_TTL:
                return res

        res = {
            'regime': 'NEUTRAL',
            'score_adj': 0,
            'reason': '',
            'tnx_5d_change_pct': 0.0,
            'uup_5d_change_pct': 0.0,
            'credit_risk_ratio': 1.0,
            'is_high_risk': False
        }

        try:
            # Download 10-Year Yield, Dollar Index ETF, HYG, TLT
            tickers = ['^TNX', 'UUP', 'HYG', 'TLT']
            data = yf.download(tickers, period='10d', progress=False)['Close']

            if data.empty:
                _MACRO_CACHE['cached_result'] = (now, res)
                return res

            tnx = data['^TNX'].dropna() if '^TNX' in data else None
            uup = data['UUP'].dropna() if 'UUP' in data else None
            hyg = data['HYG'].dropna() if 'HYG' in data else None
            tlt = data['TLT'].dropna() if 'TLT' in data else None

            tnx_chg = 0.0
            if tnx is not None and len(tnx) >= 5:
                tnx_chg = (tnx.iloc[-1] - tnx.iloc[-5]) / tnx.iloc[-5] * 100.0

            uup_chg = 0.0
            if uup is not None and len(uup) >= 5:
                uup_chg = (uup.iloc[-1] - uup.iloc[-5]) / uup.iloc[-5] * 100.0

            credit_ratio = 1.0
            if hyg is not None and tlt is not None and len(hyg) > 0 and len(tlt) > 0:
                credit_ratio = float(hyg.iloc[-1] / tlt.iloc[-1])

            res['tnx_5d_change_pct'] = round(tnx_chg, 2)
            res['uup_5d_change_pct'] = round(uup_chg, 2)
            res['credit_risk_ratio'] = round(credit_ratio, 2)

            # High Risk Rule: 10Y Yields up > 3% AND Dollar up > 1% in 5 days
            if tnx_chg > 3.0 and uup_chg > 1.0:
                res['regime'] = 'HIGH_MACRO_RISK'
                res['score_adj'] = -15
                res['is_high_risk'] = True
                res['reason'] = f"HIGH_MACRO_RISK: Yields(+{tnx_chg:.1f}%) & Dollar(+{uup_chg:.1f}%) Spiking!"
            elif tnx_chg < -1.0 and uup_chg < -0.5:
                res['regime'] = 'BULL_STABLE'
                res['score_adj'] = 5
                res['reason'] = f"BULL_STABLE_MACRO: Yields({tnx_chg:.1f}%) & Dollar({uup_chg:.1f}%) Easing"
            else:
                res['regime'] = 'NEUTRAL'
                res['score_adj'] = 0
                res['reason'] = f"NEUTRAL_MACRO: Yields({tnx_chg:+.1f}%) Dollar({uup_chg:+.1f}%)"

            _MACRO_CACHE['cached_result'] = (now, res)
            return res
        except Exception as e:
            logger.debug("Macro Risk Matrix failed: {}", e)
            _MACRO_CACHE['cached_result'] = (now, res)
            return res
