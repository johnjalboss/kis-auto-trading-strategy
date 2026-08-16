"""
Opening Spread Guard (opening_spread_guard.py)
==============================================
Protects against excessive market-maker spreads during US market opening (23:30 - 23:45 KST).
If the real-time bid-ask spread exceeds MAX_ALLOWED_SPREAD_PCT (0.35%), entry is temporarily delayed.
"""

from typing import Dict, Any
from loguru import logger
import config

class OpeningSpreadGuard:
    """Guards against wide opening spreads and liquidity vacuums"""

    MAX_SPREAD_PCT = 0.35  # Max 0.35% bid-ask spread allowed

    def __init__(self, max_spread_pct: float = MAX_SPREAD_PCT):
        self.max_spread_pct = max_spread_pct

    def check_spread(self, symbol: str, trader_instance=None) -> Dict[str, Any]:
        """
        Evaluates whether the symbol's current spread is tight enough for institutional entry.
        """
        if trader_instance is None:
            try:
                from trader import get_trader
                trader_instance = get_trader()
            except Exception:
                return {"allowed": True, "spread_pct": 0.0, "reason": "Trader unavailable"}

        try:
            spread = trader_instance.get_spread(symbol)
            spread_pct = spread * 100.0

            if spread > (self.max_spread_pct / 100.0):
                logger.warning("🚨 [SPREAD_GUARD] {} Spread too wide: {:.3f}% > {:.2f}%. Deferring entry!",
                               symbol, spread_pct, self.max_spread_pct)
                return {
                    "allowed": False,
                    "spread_pct": spread_pct,
                    "reason": f"Wide spread ({spread_pct:.2f}% > {self.max_spread_pct:.2f}%)"
                }

            logger.debug("✅ [SPREAD_GUARD] {} Spread healthy: {:.3f}% <= {:.2f}%",
                         symbol, spread_pct, self.max_spread_pct)
            return {"allowed": True, "spread_pct": spread_pct, "reason": "Spread healthy"}
        except Exception as e:
            logger.debug("Opening spread check skipped for {}: {}", symbol, e)
            return {"allowed": True, "spread_pct": 0.0, "reason": f"Check error: {e}"}

def get_opening_spread_guard() -> OpeningSpreadGuard:
    return OpeningSpreadGuard()
