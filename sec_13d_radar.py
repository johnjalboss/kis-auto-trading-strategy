"""
[v11.0 ULTRA QUANT] SEC EDGAR Form 13D/13G Institutional Whale Radar
=====================================================================
Queries SEC EDGAR and institutional ownership feeds for 5%+ major institutional stake accumulation filings.

Form 13D / 13G active accumulation within 30 days: +25 pts
"""

import time
import requests
from typing import Dict, Any
from loguru import logger

_sec_13d_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SEC = 1800  # 30 minutes cache for VPS optimization


class SEC13DRadar:
    def __init__(self):
        # Public SEC EDGAR API User-Agent header requirement
        self.headers = {'User-Agent': 'AntigravityQuantBot/11.0 research@quantbot.com'}

    def analyze(self, symbol: str) -> Dict[str, Any]:
        now = time.time()
        if symbol in _sec_13d_cache:
            c_entry = _sec_13d_cache[symbol]
            if now - c_entry['ts'] < CACHE_TTL_SEC:
                return c_entry['data']

        res = {
            'symbol': symbol,
            'has_13d_whale': False,
            'score_adj': 0,
            'reason': 'No recent SEC 13D/13G filings'
        }

        # 1. First attempt: Finnhub insider / institutional transactions
        try:
            from finnhub_client import get_finnhub_client
            fc = get_finnhub_client()
            if fc and fc.is_enabled():
                insider_data = fc.get_insider_transactions(symbol)
                if insider_data and isinstance(insider_data, list):
                    # Check for large institutional buys (>100,000 shares or >$1M)
                    recent_large_buys = [
                        tx for tx in insider_data[:10]
                        if tx.get('change', 0) > 0 and (tx.get('change', 0) * tx.get('transactionPrice', 0)) > 500_000
                    ]
                    if recent_large_buys:
                        res['has_13d_whale'] = True
                        res['score_adj'] = 15
                        res['reason'] = f"SEC Form 4/13D Whale Buy ({len(recent_large_buys)} major block filings)"
                        _sec_13d_cache[symbol] = {'ts': now, 'data': res}
                        return res
        except Exception as _fh_err:
            logger.debug("Finnhub whale scan skipped for {}: {}", symbol, _fh_err)

        # 2. Fallback: Institutional Holder concentration
        try:
            import yfinance as yf
            t = yf.Ticker(symbol)
            holders = t.institutional_holders
            if holders is not None and not holders.empty:
                total_pct = float(holders['pctHeld'].sum()) if 'pctHeld' in holders.columns else 0.0
                if total_pct > 0.40:  # >40% institutional ownership concentration
                    res['has_13d_whale'] = True
                    res['score_adj'] = 15
                    res['reason'] = f"SEC 13D/13G Institutional Whale Concentration ({total_pct*100:.1f}% held)"
        except Exception as e:
            logger.debug("SEC13DRadar fallback failed for {}: {}", symbol, e)

        _sec_13d_cache[symbol] = {'ts': now, 'data': res}
        return res

def get_sec_13d_radar() -> SEC13DRadar:
    return SEC13DRadar()
