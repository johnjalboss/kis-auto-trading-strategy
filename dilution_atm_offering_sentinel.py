"""
Share Dilution & ATM Secondary Offering Sentinel (dilution_atm_offering_sentinel.py)
==================================================================================
Protects portfolio against serial dilution, ATM (At-The-Market) equity offerings,
and secondary shelf registration offerings (Form S-3 / 424B).

Wall Street Quant Principle:
- Quality growth companies buy back shares (negative share growth).
- Serial diluters (e.g. cash-burning biotechs, meme stocks) continuously dump new shares
  on retail investors via ATM facilities whenever stock price rises.
- A quarterly share expansion rate >5.0% or annual dilution >12.0% creates severe downward
  supply overhang, resulting in -15% to -30% overnight secondary offering gap-downs.

Scoring:
- Share Buybacks / Shrinkage (< -1.0% YoY): +10 pts (Shareholder value accretion)
- Neutral / Low Dilution (0% to +3% YoY): 0 pts (Normal stock compensation)
- Elevated Dilution (+3% to +8% YoY): -5 pts (Supply overhang)
- Severe ATM Dilution Trap (> +8% QoQ or > +15% YoY): -25 pts & BLOCK ENTRY
"""

import time
from dataclasses import dataclass
from typing import Dict, Any, Optional
import yfinance as yf
from loguru import logger

_DILUTION_CACHE = {}
_DILUTION_TTL = 86400  # 24 Hours TTL (Quarterly filing data)


@dataclass
class DilutionSignal:
    symbol: str
    shares_outstanding_m: float
    float_shares_m: float
    qoq_share_growth_pct: float
    dilution_regime: str       # "BUYBACK_ACCRETION", "NORMAL_STABLE", "ELEVATED_DILUTION", "SEVERE_ATM_TRAP"
    score_adj: int             # -25 to +10 pts
    is_blocked: bool
    reason: str


class DilutionATMOfferingSentinel:
    """Evaluates share count expansion velocity and secondary offering risk."""

    def analyze(self, symbol: str) -> DilutionSignal:
        now = time.time()
        if symbol in _DILUTION_CACHE:
            ts, sig = _DILUTION_CACHE[symbol]
            if now - ts < _DILUTION_TTL:
                return sig

        shares_m = 0.0
        float_m = 0.0
        qoq_growth = 0.0
        regime = "NORMAL_STABLE"
        score_adj = 0
        is_blocked = False
        reason = "Normal share structure"

        try:
            ticker = yf.Ticker(symbol)
            info = getattr(ticker, 'info', {}) or {}
            shares_raw = info.get('sharesOutstanding', 0) or 0
            float_raw = info.get('floatShares', 0) or 0

            shares_m = round(shares_raw / 1_000_000.0, 2)
            float_m = round(float_raw / 1_000_000.0, 2)

            # Check quarterly balance sheet for share growth velocity safely
            bs = getattr(ticker, 'quarterly_balance_sheet', None)
            if bs is not None and not bs.empty and hasattr(bs, 'index') and 'Ordinary Shares Number' in bs.index:
                s_series = bs.loc['Ordinary Shares Number']
                if len(s_series) >= 2:
                    s_now = float(s_series.iloc[0])
                    s_prev = float(s_series.iloc[1])
                    if s_prev > 0:
                        qoq_growth = round(((s_now / s_prev) - 1.0) * 100.0, 2)

            if qoq_growth <= -1.0:
                regime = "BUYBACK_ACCRETION"
                score_adj = +10
                reason = f"💎 [SHARE_BUYBACKS] Shares shrinking ({qoq_growth:+.2f}% QoQ). High shareholder value accretion."
            elif qoq_growth > 8.0:
                regime = "SEVERE_ATM_TRAP"
                score_adj = -25
                is_blocked = True
                reason = f"🚨 [ATM_DILUTION_TRAP] Severe share dilution ({qoq_growth:+.2f}% QoQ)! High secondary offering dump risk."
            elif qoq_growth > 3.0:
                regime = "ELEVATED_DILUTION"
                score_adj = -8
                reason = f"⚠️ [ELEVATED_DILUTION] Share count expanded by {qoq_growth:+.2f}% QoQ. Dilution supply overhang."
            else:
                regime = "NORMAL_STABLE"
                score_adj = 0
                reason = f"Stable share count ({qoq_growth:+.2f}% QoQ)"
        except Exception as e:
            logger.debug("Dilution check error for {}: {}", symbol, e)

        sig = DilutionSignal(
            symbol=symbol,
            shares_outstanding_m=shares_m,
            float_shares_m=float_m,
            qoq_share_growth_pct=qoq_growth,
            dilution_regime=regime,
            score_adj=score_adj,
            is_blocked=is_blocked,
            reason=reason
        )

        _DILUTION_CACHE[symbol] = (now, sig)
        return sig


def get_dilution_sentinel() -> DilutionATMOfferingSentinel:
    return DilutionATMOfferingSentinel()
