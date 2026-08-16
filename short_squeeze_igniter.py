"""
Short Squeeze Igniter & Float Pressure Engine (short_squeeze_igniter.py)
========================================================================
Institutional Short Squeeze Explosive Momentum Engine.

Detects high Short Interest (% of float) and Days to Cover (DTC) combined
with Breakout Relative Volume to capture explosive short covering margin cascades.

Scoring:
- High Short Interest (>15%) + Breakout Volume (>2.0x): +20 pts (Squeeze Ignition)
- Moderate Short Interest (8-15%) + High DTC (>4 days): +10 pts (Covering Pressure)
- Low Short Interest (<3%): 0 pts (Organic Trend)
"""

import time
from dataclasses import dataclass
from typing import Dict, Any, Optional
import yfinance as yf
from loguru import logger

_SQUEEZE_CACHE = {}
_SQUEEZE_TTL = 14400  # 4 Hours TTL


@dataclass
class SqueezeSignal:
    symbol: str
    short_pct_float: float     # e.g. 15.4%
    days_to_cover: float       # e.g. 4.8 days
    short_shares_millions: float
    is_squeeze_candidate: bool
    score_bonus: int           # 0 to +20 pts
    reason: str


class ShortSqueezeIgniter:
    """Evaluates short squeeze ignition potential."""

    def analyze(self, symbol: str, rvol: float = 1.0) -> SqueezeSignal:
        now = time.time()
        if symbol in _SQUEEZE_CACHE:
            ts, sig = _SQUEEZE_CACHE[symbol]
            if now - ts < _SQUEEZE_TTL:
                return sig

        short_pct = 0.0
        dtc = 0.0
        shares_short = 0.0

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info if hasattr(ticker, 'fast_info') else {}
            # Fallback to general info if available
            raw_info = getattr(ticker, 'info', {}) or {}

            short_pct = raw_info.get('shortPercentOfFloat', 0.0) or 0.0
            if short_pct > 0 and short_pct < 1.0:
                short_pct *= 100.0  # Convert 0.15 -> 15.0%

            dtc = raw_info.get('shortRatio', 0.0) or 0.0
            shares_short = (raw_info.get('sharesShort', 0) or 0) / 1_000_000.0
        except Exception as e:
            logger.debug("Short interest fetch failed for {}: {}", symbol, e)

        score_bonus = 0
        is_candidate = False
        reason = "Normal short interest profile"

        if short_pct >= 15.0 and (dtc >= 3.5 or rvol >= 1.8):
            score_bonus = +20
            is_candidate = True
            reason = f"🚀 [SHORT_SQUEEZE_IGNITION] High Short Interest ({short_pct:.1f}%), DTC {dtc:.1f}d, RVOL {rvol:.1f}x"
        elif short_pct >= 8.0 and dtc >= 4.0:
            score_bonus = +10
            is_candidate = True
            reason = f"⚡ [SHORT_COVERING_PRESSURE] Moderate Short ({short_pct:.1f}%), High DTC ({dtc:.1f}d)"
        elif dtc >= 5.0:
            score_bonus = +5
            reason = f"DTC elevated ({dtc:.1f}d) - Extended covering needed"

        sig = SqueezeSignal(
            symbol=symbol,
            short_pct_float=round(short_pct, 2),
            days_to_cover=round(dtc, 2),
            short_shares_millions=round(shares_short, 2),
            is_squeeze_candidate=is_candidate,
            score_bonus=score_bonus,
            reason=reason
        )

        _SQUEEZE_CACHE[symbol] = (now, sig)
        return sig


def get_short_squeeze_igniter() -> ShortSqueezeIgniter:
    return ShortSqueezeIgniter()
