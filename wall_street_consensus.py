"""
Wall Street Consensus Sentinel (wall_street_consensus.py)
=========================================================
Tracks institutional analyst recommendation trends (Goldman Sachs, Morgan Stanley, JPM, etc.)
via Finnhub's /stock/recommendation endpoint.

Mathematical Model:
    Total = StrongBuy + Buy + Hold + Sell + StrongSell
    BullishRatio = (StrongBuy + Buy) / Total
    ConsensusScore = (2*StrongBuy + 1*Buy - 1*Sell - 2*StrongSell) / (2*Total) * 100  [-100 to +100]

Decision Rules:
    - ConsensusScore >= 50 (Strong Institutional Backing): +10pt Consensus Bonus
    - ConsensusScore <= -20 (Institutional Sell Rating): Rejection / Block
"""

import os
import time
import requests
from dataclasses import dataclass
from typing import Dict, Any, Optional
from loguru import logger
import config

@dataclass
class ConsensusResult:
    symbol: str
    total_analysts: int
    strong_buy: int
    buy: int
    hold: int
    sell: int
    strong_sell: int
    bullish_ratio: float      # e.g. 0.75 (75% buy/strong buy)
    consensus_score: float    # -100 to +100
    is_strong_consensus: bool # True if score >= 50
    is_blocked: bool          # True if score <= -20
    reason: str


class WallStreetConsensusSentinel:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WallStreetConsensusSentinel, cls).__new__(cls)
            cls._instance._cache = {}
            cls._instance._cache_ttl = 86400  # 24 hours (ratings update slowly)
        return cls._instance

    def analyze(self, symbol: str) -> ConsensusResult:
        """Fetches and evaluates Wall Street institutional ratings."""
        now = time.time()
        sym = symbol.upper().strip()

        # Check in-memory cache
        if sym in self._cache:
            entry = self._cache[sym]
            if now - entry['timestamp'] < self._cache_ttl:
                return entry['result']

        default_result = ConsensusResult(
            symbol=sym,
            total_analysts=0,
            strong_buy=0,
            buy=0,
            hold=0,
            sell=0,
            strong_sell=0,
            bullish_ratio=0.5,
            consensus_score=0.0,
            is_strong_consensus=False,
            is_blocked=False,
            reason="NO_DATA"
        )

        api_key = getattr(config, 'FINNHUB_API_KEY', '') or os.getenv('FINNHUB_API_KEY', '')
        if not api_key:
            return default_result

        url = f"https://finnhub.io/api/v1/stock/recommendation?symbol={sym}&token={api_key}"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    latest = data[0]  # Most recent month
                    sb = int(latest.get('strongBuy', 0))
                    b = int(latest.get('buy', 0))
                    h = int(latest.get('hold', 0))
                    s = int(latest.get('sell', 0))
                    ss = int(latest.get('strongSell', 0))
                    total = sb + b + h + s + ss

                    if total > 0:
                        bullish_ratio = (sb + b) / total
                        # Score between -100 and +100
                        raw_score = (2 * sb + 1 * b - 1 * s - 2 * ss) / (2 * total) * 100.0
                        score = max(-100.0, min(100.0, raw_score))

                        is_strong = (score >= 45.0 and bullish_ratio >= 0.60)
                        is_blocked = (score <= -20.0 or (s + ss) > (sb + b))

                        reason = ""
                        if is_strong:
                            reason = f"STRONG_CONSENSUS: {bullish_ratio:.0%} Buy/StrongBuy ({sb+b}/{total} analysts)"
                        elif is_blocked:
                            reason = f"ANALYST_SELL_OVERHANG: {s+ss}/{total} Sell ratings (Score {score:+.0f})"
                        else:
                            reason = f"NEUTRAL_CONSENSUS: Score {score:+.0f} ({sb+b} Buy, {h} Hold, {s+ss} Sell)"

                        res = ConsensusResult(
                            symbol=sym,
                            total_analysts=total,
                            strong_buy=sb,
                            buy=b,
                            hold=h,
                            sell=s,
                            strong_sell=ss,
                            bullish_ratio=bullish_ratio,
                            consensus_score=score,
                            is_strong_consensus=is_strong,
                            is_blocked=is_blocked,
                            reason=reason
                        )

                        self._cache[sym] = {'timestamp': now, 'result': res}
                        return res

        except Exception as e:
            logger.debug("Wall Street consensus fetch failed for {}: {}", sym, e)

        return default_result


def get_wall_street_consensus() -> WallStreetConsensusSentinel:
    return WallStreetConsensusSentinel()
