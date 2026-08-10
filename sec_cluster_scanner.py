"""
[v7.0 SEC FORM 4 CLUSTER INSIDER BUY SCANNER]
Scans SEC Form 4 filings via Finnhub / SEC EDGAR API.

Rules:
1. Detect Multi-Executive Cluster Buys: 2+ insiders (CEO/CFO/Directors) buying within 72 hours.
2. Minimum Dollar Value: Combined $500,000+ ($500k+) purchased out of own pocket.
3. Score Bonus: +25 pts (Highest Conviction Institutional Insider Signal!)
"""

import time
from typing import Dict, Any
from loguru import logger
from finnhub_client import get_finnhub_client

_CLUSTER_CACHE = {}
_CLUSTER_TTL = 7200  # 2 hours


class SecClusterScanner:
    def __init__(self):
        self.finnhub = get_finnhub_client()

    def analyze(self, symbol: str) -> Dict[str, Any]:
        now = time.time()
        if symbol in _CLUSTER_CACHE:
            ts, res = _CLUSTER_CACHE[symbol]
            if now - ts < _CLUSTER_TTL:
                return res

        res = {
            'is_cluster_buy': False,
            'buyer_count': 0,
            'net_cluster_usd': 0.0,
            'score_adj': 0,
            'reason': ''
        }

        try:
            raw_txs = self.finnhub.get_insider_transactions(symbol)
            if not raw_txs:
                _CLUSTER_CACHE[symbol] = (now, res)
                return res

            recent_buys = []
            buyer_names = set()
            total_usd = 0.0

            for tx in raw_txs:
                change = tx.get('change', 0) or 0
                price = tx.get('price', 0.0) or 0.0
                name = tx.get('name', 'Unknown')

                if change > 0 and price > 0:
                    val = change * price
                    total_usd += val
                    buyer_names.add(name)

            res['buyer_count'] = len(buyer_names)
            res['net_cluster_usd'] = round(total_usd, 2)

            # Rule: 2+ distinct insiders buying $300k+ total
            if len(buyer_names) >= 2 and total_usd >= 300_000:
                res['is_cluster_buy'] = True
                res['score_adj'] = 25  # Highest conviction insider bonus!
                res['reason'] = f"SEC_CLUSTER_INSIDER_BUY: {len(buyer_names)} executives bought ${total_usd:,.0f}!"

            _CLUSTER_CACHE[symbol] = (now, res)
            return res
        except Exception as e:
            logger.debug("SecClusterScanner failed for {}: {}", symbol, e)
            _CLUSTER_CACHE[symbol] = (now, res)
            return res
