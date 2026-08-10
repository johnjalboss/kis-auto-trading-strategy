"""
Options Flow Analyzer
======================
Institutional-grade options market intelligence for the trading bot.

Features:
  - Max Pain  (weekly options expiry price magnet)
  - Gamma Exposure (GEX)  (dealer hedging direction + magnitude)
  - IV Rank / IV Percentile  (vol regime: cheap vs expensive)
  - 1σ / 2σ Sigma Range  (options-implied expected move)
  - Put/Call Ratio  (market sentiment)
  - VIX Regime  (macro fear filter)

Data Source:
  - yfinance options chain (bypasses our KIS shim via yf._original_yf_Ticker)
  - CBOE public data for VIX / aggregate P/C ratio

RAM Optimization:
  - Per-symbol TTL cache (30 min for options, 10 min for VIX)
  - Lightweight dataclasses (no large DataFrames stored)
  - Lazy fetch — only computed when needed, not at startup
  - Automatic cache eviction to prevent memory leaks
"""

from __future__ import annotations

import time
import datetime
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict
import math
import os
import threading

from loguru import logger

def _run_with_timeout(func, args=(), kwargs={}, timeout=2.0):
    """Run a function in a background thread and return its result, or None if it times out."""
    result = [None]
    exception = [None]
    
    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e
            
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout)
    
    if thread.is_alive():
        return None
    if exception[0]:
        raise exception[0]
    return result[0]


# ──────────────────────────────────────────────────────────
# Cache constants
# ──────────────────────────────────────────────────────────
_OPTIONS_TTL   = 14400  # 4 hours — standard options OI only updates once daily, safe from IP bans
_VIX_TTL       = 600    # 10 min — VIX updates each minute
_MAX_CACHE_SIZE = 30    # evict oldest when > 30 symbols cached
_FALLBACK_IV    = 0.25  # assume 25% IV when data unavailable


# ──────────────────────────────────────────────────────────
# Result dataclass (tiny — only scalars, no DataFrames)
# ──────────────────────────────────────────────────────────
@dataclass
class OptionsSnapshot:
    symbol:           str
    price:            float      = 0.0
    max_pain:         float      = 0.0   # Max pain strike
    gex:              float      = 0.0   # Net Gamma Exposure ($ billions proxy)
    iv_rank:          float      = 0.0   # 0-100 (50 = median)
    iv_current:       float      = 0.0   # Current implied volatility (annualised)
    sigma_low_1:      float      = 0.0   # 1σ lower bound (weekly)
    sigma_high_1:     float      = 0.0   # 1σ upper bound (weekly)
    sigma_low_2:      float      = 0.0   # 2σ lower bound (weekly)
    sigma_high_2:     float      = 0.0   # 2σ upper bound (weekly)
    put_call_ratio:   float      = 1.0   # <0.7 bullish, >1.2 bearish
    iv_skew:          float      = 0.0   # Put IV - Call IV (negative = Call Skew / Bullish)
    unusual_oi_ratio: float      = 1.0   # OTM Call OI spike ratio (>2.5x = Smart Money Sweep)
    days_to_expiry:   int        = 0     # DTE for nearest weekly
    is_expiry_week:   bool       = False # True if expiry within 5 calendar days
    score:            int        = 0     # Composite options score (-20 to +20)
    reason:           str        = ""
    fetched_at:       float      = field(default_factory=time.time)

    def is_fresh(self, ttl: float = _OPTIONS_TTL) -> bool:
        return (time.time() - self.fetched_at) < ttl


@dataclass
class VixSnapshot:
    vix:          float   = 20.0   # Current VIX
    regime:       str     = "NORMAL"  # LOW / NORMAL / ELEVATED / EXTREME
    score_adj:    int     = 0         # Score adjustment from VIX
    fetched_at:   float   = field(default_factory=time.time)

    def is_fresh(self) -> bool:
        return (time.time() - self.fetched_at) < _VIX_TTL


# ──────────────────────────────────────────────────────────
# Internal cache
# ──────────────────────────────────────────────────────────
_options_cache: Dict[str, OptionsSnapshot] = {}
_vix_cache: Optional[VixSnapshot] = None


def _evict_old_cache():
    """Remove stale entries if cache grows too large."""
    global _options_cache
    if len(_options_cache) <= _MAX_CACHE_SIZE:
        return
    # Sort by fetch time, remove oldest half
    sorted_keys = sorted(_options_cache.keys(),
                         key=lambda k: _options_cache[k].fetched_at)
    for k in sorted_keys[:len(sorted_keys) // 2]:
        del _options_cache[k]


# ──────────────────────────────────────────────────────────
# Helper: get real yfinance Ticker (bypassing our KIS shim)
# ──────────────────────────────────────────────────────────
def _get_real_ticker(symbol: str):
    """
    Returns the genuine yfinance Ticker, bypassing the KIS proxy shim.
    The shim stores the original class on yf._original_yf_Ticker.
    """
    try:
        import yfinance as yf
        OriginalTicker = getattr(yf, '_original_yf_Ticker', None)
        if OriginalTicker is None:
            # Shim not active — just use yf.Ticker directly
            return yf.Ticker(symbol)
        return OriginalTicker(symbol)
    except Exception as e:
        logger.debug("Could not get real yfinance Ticker for {}: {}", symbol, e)
        return None


# ──────────────────────────────────────────────────────────
# VIX Regime Fetcher
# ──────────────────────────────────────────────────────────
def get_vix_snapshot() -> VixSnapshot:
    """Fetch VIX level with 10-min cache."""
    global _vix_cache
    if _vix_cache and _vix_cache.is_fresh():
        return _vix_cache

    snap = VixSnapshot()
    # Volatility Fetching: Bypassing DISABLE_OPTIONS_FLOW check for VIX since it is cached 
    # for 10 minutes and does not download options chain, making it completely safe from IP bans.
    # This ensures VIX crash guards and volatility score adjustments remain active.
    # (If VIX fetch fails, it gracefully falls back to default 20.0 NORMAL regime)

    try:
        ticker = _get_real_ticker("^VIX")
        if ticker is None:
            return snap

        info = _run_with_timeout(lambda: ticker.fast_info, timeout=2.0)
        vix = None
        if info:
            vix = getattr(info, 'last_price', None) or getattr(info, 'regularMarketPrice', None)

        if vix and vix > 0:
            snap.vix = float(vix)
            if snap.vix < 15:
                snap.regime = "LOW"
                snap.score_adj = +5   # Low fear → favour entries
            elif snap.vix < 20:
                snap.regime = "NORMAL"
                snap.score_adj = +3
            elif snap.vix < 28:
                snap.regime = "ELEVATED"
                snap.score_adj = -3  # Caution
            elif snap.vix < 35:
                snap.regime = "HIGH"
                snap.score_adj = -7
            else:
                snap.regime = "EXTREME"
                snap.score_adj = -15  # Crash mode
        else:
            logger.debug("VIX data unavailable, using default")

    except Exception as e:
        logger.debug("VIX fetch failed: {}", e)

    _vix_cache = snap
    return snap


# ──────────────────────────────────────────────────────────
# Days to nearest weekly expiry
# ──────────────────────────────────────────────────────────
def _nearest_expiry_date(expiries: tuple) -> Optional[str]:
    """Return the next Friday (weekly) expiry or nearest listed expiry."""
    now = datetime.date.today()
    futures = [d for d in expiries if datetime.date.fromisoformat(d) >= now]
    if not futures:
        return None
    # Prefer the soonest expiry (usually this week's or next week's Friday)
    return min(futures, key=lambda d: datetime.date.fromisoformat(d))


def _days_to_friday() -> int:
    now = datetime.date.today()
    friday = 4  # Mon=0, Fri=4
    days = (friday - now.weekday()) % 7
    return days if days > 0 else 7  # next Friday if today is Friday


# ──────────────────────────────────────────────────────────
# Core options analytics
# ──────────────────────────────────────────────────────────
def _compute_options_snapshot(symbol: str) -> OptionsSnapshot:
    """
    Fetch option chain and compute: Max Pain, GEX, IV Rank, Sigma Range, P/C.
    Uses only the nearest weekly expiry to minimise memory usage.
    """
    snap = OptionsSnapshot(symbol=symbol)

    if os.getenv("DISABLE_OPTIONS_FLOW", "false").lower() == "true":
        snap.reason = "options_disabled"
        _fill_sigma_fallback(snap)
        return snap

    ticker = _get_real_ticker(symbol)
    if ticker is None:
        snap.reason = "no_ticker"
        return snap

    # ── Current price ──
    try:
        fi = _run_with_timeout(lambda: ticker.fast_info, timeout=2.0)
        price = 0
        if fi:
            price = getattr(fi, 'last_price', 0) or getattr(fi, 'regularMarketPrice', 0)
        snap.price = float(price) if price else 0.0
    except Exception:
        snap.price = 0.0

    if snap.price <= 0:
        snap.reason = "no_price"
        return snap

    # ── Options chain ──
    try:
        expiries = _run_with_timeout(lambda: ticker.options, timeout=5.0)
    except Exception as e:
        logger.debug("options.options list failed for {}: {}", symbol, e)
        snap.reason = "no_expiries"
        _fill_sigma_fallback(snap)
        return snap

    if not expiries:
        snap.reason = "no_expiries"
        _fill_sigma_fallback(snap)
        return snap

    target_expiry = _nearest_expiry_date(expiries)
    if not target_expiry:
        snap.reason = "no_future_expiry"
        _fill_sigma_fallback(snap)
        return snap

    exp_date = datetime.date.fromisoformat(target_expiry)
    snap.days_to_expiry = (exp_date - datetime.date.today()).days
    snap.is_expiry_week = snap.days_to_expiry <= 5

    try:
        import pandas as pd
        chain = _run_with_timeout(lambda: ticker.option_chain(target_expiry), timeout=5.0)
        if chain is None:
            raise TimeoutError("options chain download timed out")
        calls = chain.calls
        puts  = chain.puts
    except Exception as e:
        logger.debug("option_chain failed for {} ({}): {}", symbol, target_expiry, e)
        snap.reason = "chain_error"
        _fill_sigma_fallback(snap)
        return snap

    if calls.empty or puts.empty:
        snap.reason = "empty_chain"
        _fill_sigma_fallback(snap)
        return snap

    # Ensure required columns exist
    req_cols = {'strike', 'openInterest', 'impliedVolatility'}
    if not req_cols.issubset(calls.columns) or not req_cols.issubset(puts.columns):
        snap.reason = "missing_cols"
        _fill_sigma_fallback(snap)
        return snap

    # ── Max Pain ──
    snap.max_pain = _calc_max_pain(calls, puts, snap.price)

    # ── Gamma Exposure (GEX) ──
    snap.gex = _calc_gex(calls, puts, snap.price, snap.days_to_expiry)

    # ── IV: use ATM options average & Skew ──
    snap.iv_current, snap.iv_rank = _calc_iv(calls, puts, snap.price)
    
    # ── Volatility Skew & Unusual OI Sweeps ──
    snap.iv_skew = _calc_iv_skew(calls, puts, snap.price)
    snap.unusual_oi_ratio = _calc_unusual_oi_sweep(calls, puts, snap.price)

    # ── Sigma Range (1σ / 2σ weekly move) ──
    _fill_sigma(snap)

    # ── Put/Call Ratio (by open interest) ──
    total_call_oi = calls['openInterest'].fillna(0).sum()
    total_put_oi  = puts['openInterest'].fillna(0).sum()
    if total_call_oi > 0:
        snap.put_call_ratio = round(total_put_oi / total_call_oi, 3)

    # ── Composite Score ──
    snap.score, snap.reason = _score_options(snap)
    return snap


def _fill_sigma_fallback(snap: OptionsSnapshot):
    """Fill sigma range using assumed 25% IV when chain unavailable."""
    snap.iv_current = _FALLBACK_IV
    snap.iv_rank = 50.0
    _fill_sigma(snap)


def _fill_sigma(snap: OptionsSnapshot):
    """
    Expected weekly move = price × IV × sqrt(DTE/365).
    DTE defaults to nearest Friday if unknown.
    """
    dte = snap.days_to_expiry if snap.days_to_expiry > 0 else _days_to_friday()
    iv  = snap.iv_current if snap.iv_current > 0 else _FALLBACK_IV
    price = snap.price

    weekly_move_1 = price * iv * math.sqrt(dte / 365.0)
    weekly_move_2 = weekly_move_1 * 2.0

    snap.sigma_low_1  = round(price - weekly_move_1, 2)
    snap.sigma_high_1 = round(price + weekly_move_1, 2)
    snap.sigma_low_2  = round(price - weekly_move_2, 2)
    snap.sigma_high_2 = round(price + weekly_move_2, 2)


def _calc_max_pain(calls, puts, price: float) -> float:
    """
    Standard Max Pain: find strike where total option value is minimised.
    Uses open interest weighted ITM intrinsic value calculation.
    """
    try:
        all_strikes = sorted(set(calls['strike'].tolist()) | set(puts['strike'].tolist()))
        if not all_strikes:
            return price

        call_oi = calls.set_index('strike')['openInterest'].fillna(0)
        put_oi  = puts.set_index('strike')['openInterest'].fillna(0)

        min_pain = None
        max_pain_strike = price

        for test_strike in all_strikes:
            # Call holders lose when price < strike → calls worthless below test_strike
            call_pain = sum(
                max(0.0, test_strike - s) * call_oi.get(s, 0)
                for s in all_strikes
            )
            # Put holders lose when price > strike → puts worthless above test_strike
            put_pain = sum(
                max(0.0, s - test_strike) * put_oi.get(s, 0)
                for s in all_strikes
            )
            total = call_pain + put_pain
            if min_pain is None or total < min_pain:
                min_pain = total
                max_pain_strike = test_strike

        return float(max_pain_strike)
    except Exception as e:
        logger.debug("Max pain calc failed: {}", e)
        return price


def _calc_gex(calls, puts, price: float, dte: int) -> float:
    """
    Simplified Gamma Exposure (GEX):
    GEX = Σ(call_OI - put_OI) × gamma_proxy × 100 (shares) × price

    gamma_proxy ≈ N(d1) for ATM options as simplified estimate.
    Positive GEX → dealer long gamma → market likely to stay in range (stabilising)
    Negative GEX → dealer short gamma → market likely to amplify moves (volatile)
    """
    try:
        dte_y = max(dte, 1) / 365.0
        iv_col = 'impliedVolatility'

        def atm_call_gamma(row) -> float:
            k = row['strike']
            iv = row.get(iv_col, 0.25) or 0.25
            oi = row.get('openInterest', 0) or 0
            if k <= 0 or iv <= 0 or oi <= 0:
                return 0
            d1 = (math.log(price / k) + 0.5 * iv ** 2 * dte_y) / (iv * math.sqrt(dte_y))
            gamma = math.exp(-0.5 * d1 ** 2) / (price * iv * math.sqrt(2 * math.pi * dte_y))
            return gamma * oi * 100 * price  # notional

        call_gex = sum(atm_call_gamma(row) for _, row in calls.iterrows()
                       if abs(row['strike'] - price) / price < 0.15)  # ±15% strikes only
        put_gex  = sum(atm_call_gamma(row) for _, row in puts.iterrows()
                       if abs(row['strike'] - price) / price < 0.15)

        # Net GEX (positive = stabilising, negative = amplifying)
        return round((call_gex - put_gex) / 1_000_000, 2)  # in $M
    except Exception as e:
        logger.debug("GEX calc failed: {}", e)
        return 0.0


def _calc_iv(calls, puts, price: float) -> Tuple[float, float]:
    """
    Extract ATM implied volatility and compute a rough IV rank (0-100).
    IV rank = (current_IV - 30d_low) / (30d_high - 30d_low) × 100
    Since we only have one chain, we approximate rank using VIX as proxy.
    """
    try:
        iv_col = 'impliedVolatility'

        # Get ATM strike options (closest to current price)
        atm_calls = calls.copy()
        atm_calls['dist'] = abs(atm_calls['strike'] - price)
        atm_calls = atm_calls.sort_values('dist').head(3)

        atm_puts = puts.copy()
        atm_puts['dist'] = abs(atm_puts['strike'] - price)
        atm_puts = atm_puts.sort_values('dist').head(3)

        iv_vals = []
        for _, row in atm_calls.iterrows():
            iv = row.get(iv_col, 0)
            if 0.01 < iv < 5.0:
                iv_vals.append(float(iv))
        for _, row in atm_puts.iterrows():
            iv = row.get(iv_col, 0)
            if 0.01 < iv < 5.0:
                iv_vals.append(float(iv))

        current_iv = sum(iv_vals) / len(iv_vals) if iv_vals else _FALLBACK_IV

        # IV Rank: normalise using VIX as market baseline
        vix = _vix_cache.vix if _vix_cache else 20.0
        # If stock IV is 2× VIX → IV rank ~80 (expensive), if IV ~ VIX → ~50
        iv_rank = min(100, max(0, (current_iv / (vix / 100) - 0.5) * 66.7))

        return round(current_iv, 4), round(iv_rank, 1)
    except Exception as e:
        logger.debug("IV calc failed: {}", e)
        return _FALLBACK_IV, 50.0


def _calc_iv_skew(calls, puts, price: float) -> float:
    """
    Calculate Put-Call Volatility Skew: IV(OTM Put ~5% below) - IV(OTM Call ~5% above)
    Negative Skew (< -0.03) = Call Skew (Aggressive Institutional Upside FOMO)
    Positive Skew (> +0.08) = Put Skew (Institutional Crash Insurance Buying)
    """
    try:
        import pandas as pd
        iv_col = 'impliedVolatility'
        otm_calls = calls[(calls['strike'] > price * 1.02) & (calls['strike'] < price * 1.10)]
        otm_puts  = puts[(puts['strike'] < price * 0.98) & (puts['strike'] > price * 0.90)]

        if otm_calls.empty or otm_puts.empty:
            return 0.0

        call_iv = otm_calls[iv_col].median()
        put_iv  = otm_puts[iv_col].median()

        if pd.isna(call_iv) or pd.isna(put_iv):
            return 0.0

        return round(float(put_iv - call_iv), 4)
    except Exception as e:
        logger.debug("IV Skew calc failed: {}", e)
        return 0.0


def _calc_unusual_oi_sweep(calls, puts, price: float) -> float:
    """
    Detect Unusual OI Sweep in OTM Call options.
    If OTM Call Open Interest spike ratio >= 2.5x mean, Smart Money Leverage Sweep detected!
    """
    try:
        otm_calls = calls[calls['strike'] > price * 1.01]
        if otm_calls.empty:
            return 1.0

        max_oi = otm_calls['openInterest'].max()
        avg_oi = otm_calls['openInterest'].mean()

        if avg_oi <= 0:
            return 1.0

        return round(float(max_oi / avg_oi), 2)
    except Exception as e:
        logger.debug("Unusual OI calc failed: {}", e)
        return 1.0


# ──────────────────────────────────────────────────────────
# Scoring Logic
# ──────────────────────────────────────────────────────────
def _score_options(snap: OptionsSnapshot) -> Tuple[int, str]:
    """
    Combine options signals into a single score adjustment (-20 to +20).
    Includes Advanced Quant Features:
      - Unusual OI Sweeps (>2.5x OTM call OI spike)
      - Volatility Skew (Call Skew vs Put Skew)
      - IV Crush & Max Pain Magnet
    """
    score = 0
    reasons = []

    price = snap.price

    # ── 1. Max Pain Magnet on Expiry Week ──
    if snap.is_expiry_week and price > 0 and snap.max_pain > 0:
        mp_dev = abs(price - snap.max_pain) / price
        if mp_dev < 0.015:          # Within 1.5% of max pain → dealer pin risk
            score -= 8
            reasons.append(f"MaxPain_pin(${snap.max_pain:.0f})")
        elif mp_dev < 0.03:
            score -= 4
            reasons.append(f"NearMaxPain(${snap.max_pain:.0f})")
        elif price > snap.max_pain * 1.03:
            score += 5              # Price well above max pain → bullish momentum
            reasons.append(f"AboveMaxPain(${snap.max_pain:.0f})")
        elif price < snap.max_pain * 0.97 and snap.days_to_expiry <= 3:
            score += 8              # Dealers pulling price UP to Max Pain before Friday expiry
            reasons.append(f"MaxPainUpwardPull(${snap.max_pain:.0f})")

    # ── 2. Gamma Exposure & Gamma Squeeze Surge ──
    pcr = snap.put_call_ratio
    if snap.gex < -3.0 and pcr < 0.65:
        score += 10                 # Gamma Squeeze Surge: Forced Dealer Buying
        reasons.append(f"GammaSqueezeSurge(${snap.gex:.1f}M)")
    elif snap.gex > 5.0:             # Strong positive GEX → price pin / low volatility
        score += 4
        reasons.append(f"GEX_stable(${snap.gex:.1f}M)")
    elif snap.gex < -5.0:            # Negative GEX without call surge → vol risk
        score -= 4
        reasons.append(f"GEX_volatile(${snap.gex:.1f}M)")

    # ── 3. [v4.1 ADVANCED] Volatility Skew & Unusual OI Sweeps ──
    if snap.iv_skew < -0.03:
        score += 12                 # Call Skew: Institutions aggressively buying upside OTM Calls!
        reasons.append(f"CallSkew_Bullish({snap.iv_skew:.3f})")
    elif snap.iv_skew > 0.08:
        score -= 10                 # Put Skew: Institutions hedging against downside crash
        reasons.append(f"PutSkew_Bearish({snap.iv_skew:.3f})")

    if snap.unusual_oi_ratio >= 2.5:
        score += 15                 # Unusual Whales OI Sweep: Institutional leveraged bet!
        reasons.append(f"UnusualOI_Sweep({snap.unusual_oi_ratio:.1f}x)")

    # ── 4. IV Rank & IV Crush Shield ──
    if snap.iv_rank < 25:
        score += 5                  # Low IV = underpriced vol = calm market
        reasons.append(f"IV_low({snap.iv_rank:.0f}%)")
    elif snap.iv_rank > 80:
        score -= 8                  # High IV = IV Crush Shield active
        reasons.append(f"IV_Crush_Risk({snap.iv_rank:.0f}%)")

    # ── 4. Put/Call Ratio ──
    pcr = snap.put_call_ratio
    if pcr < 0.5:
        score -= 3                  # Euphoria: excessive call buying
        reasons.append(f"PCR_euphoria({pcr:.2f})")
    elif 0.5 <= pcr < 0.7:
        score += 5                  # Moderate bullish sentiment
        reasons.append(f"PCR_bullish({pcr:.2f})")
    elif 0.7 <= pcr <= 1.0:
        score += 2                  # Neutral-slightly bullish
    elif pcr > 1.2:
        score -= 4                  # Fear → potential oversold bounce, but risky entry
        reasons.append(f"PCR_fear({pcr:.2f})")

    # ── 5. Sigma band breach (is price extended?) ──
    if price > 0 and snap.sigma_high_1 > 0:
        if price > snap.sigma_high_1:
            score -= 8              # Price outside 1σ → overshoot risk
            reasons.append(f"PriceAbove1σ(${snap.sigma_high_1:.0f})")
        elif price < snap.sigma_low_1:
            score += 6              # Oversold relative to expected range
            reasons.append(f"PriceBelow1σ(${snap.sigma_low_1:.0f})")

    score = max(-20, min(20, score))
    return score, " | ".join(reasons) if reasons else "options_OK"


# ──────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────
def get_options_snapshot(symbol: str, force_refresh: bool = False) -> OptionsSnapshot:
    """
    Main entry point. Returns a cached OptionsSnapshot for the symbol.
    Always returns a result (never raises), with graceful defaults.
    """
    global _options_cache

    if not force_refresh and symbol in _options_cache:
        cached = _options_cache[symbol]
        if cached.is_fresh():
            return cached

    # Evict stale entries first (RAM guard)
    _evict_old_cache()

    try:
        snap = _compute_options_snapshot(symbol)
        if snap.reason and snap.reason not in ("options_OK", ""):
            logger.warning("🚨 [OPTIONS_FALLBACK_ALERT] Symbol {}: Live options fetch fell back | Reason: {}", symbol, snap.reason)
    except Exception as e:
        logger.warning("options_flow: unexpected error for {}: {}", symbol, e)
        snap = OptionsSnapshot(symbol=symbol, reason=f"error:{e}")
        _fill_sigma_fallback(snap)

    _options_cache[symbol] = snap

    logger.debug(
        "OptionsFlow {}: price=${:.2f} maxpain=${:.2f} GEX={:.1f}M "
        "IV={:.0%} IVR={:.0f} PCR={:.2f} DTE={} score={:+d} | {}",
        symbol, snap.price, snap.max_pain, snap.gex,
        snap.iv_current, snap.iv_rank, snap.put_call_ratio,
        snap.days_to_expiry, snap.score, snap.reason
    )
    return snap


def get_options_score(symbol: str, current_price: float = 0.0) -> Tuple[int, str]:
    """
    Quick accessor for strategy.py — returns (score, reason).
    Score range: -20 (very bearish signal) to +20 (very bullish signal).
    """
    if os.getenv("DISABLE_OPTIONS_FLOW", "false").lower() == "true":
        return 0, "options_disabled"

    try:
        snap = get_options_snapshot(symbol)
        # If price changed significantly since cache, invalidate sigma check
        if current_price > 0 and snap.price > 0:
            if abs(current_price - snap.price) / snap.price > 0.03:
                snap.price = current_price
                _fill_sigma(snap)
                snap.score, snap.reason = _score_options(snap)
        return snap.score, snap.reason
    except Exception as e:
        logger.debug("options_flow.get_options_score failed for {}: {}", symbol, e)
        return 0, "options_unavailable"


def get_sigma_range(symbol: str) -> Tuple[float, float, float, float]:
    """
    Returns (sigma_low_1, sigma_high_1, sigma_low_2, sigma_high_2).
    Used by check_exit() to detect if price is outside expected range.
    """
    try:
        snap = get_options_snapshot(symbol)
        return snap.sigma_low_1, snap.sigma_high_1, snap.sigma_low_2, snap.sigma_high_2
    except Exception:
        return 0.0, 0.0, 0.0, 0.0


def is_near_max_pain(symbol: str, price: float, threshold_pct: float = 0.015) -> bool:
    """True if price is within threshold % of max pain on expiry week."""
    try:
        snap = get_options_snapshot(symbol)
        if not snap.is_expiry_week or snap.max_pain <= 0 or price <= 0:
            return False
        return abs(price - snap.max_pain) / price < threshold_pct
    except Exception:
        return False


def clear_cache():
    """Force clear the entire options cache (e.g., at day start)."""
    global _options_cache, _vix_cache
    _options_cache.clear()
    _vix_cache = None
    logger.info("OptionsFlow cache cleared")
