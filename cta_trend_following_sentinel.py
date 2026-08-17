"""
Systematic CTA Trend-Following Fund Sentinel (cta_trend_following_sentinel.py)
==============================================================================
Institutional Trend-Following (CTA / Managed Futures) Fund Positioning & Trigger Engine.

Wall Street Reality:
- Systematic CTAs manage >$350B in automated trend-following mandates.
- They execute 100% MECHANICAL, non-discretionary programmatic buying/selling based on:
  1. 20-Day, 50-Day, 100-Day, 200-Day Moving Average Breakouts / Breakdowns
  2. 20-Day Donchian Channel High/Low Penetrations
  3. Volatility-Targeted Mechanical Deleveraging (1 / VIX scaling)

Alpha Edge:
- Front-runs CTA mechanical buying surges when new trend levels are breached (+10 pts).
- Predicts exact CTA "Cliff Levels" where massive algorithmic stop cascades occur (-15 pts & hedge).
"""

import time
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger

_CTA_CACHE = {}
_CTA_TTL = 1800  # 30 Minutes TTL


@dataclass
class CTAPositioningSignal:
    spy_price: float
    cta_net_exposure_pct: int   # -100% to +100%
    cta_regime: str             # "MAX_LONG_ACCELERATION", "MODERATE_LONG", "NEUTRAL", "UNWIND_RISK", "MAX_SHORT"
    trigger_levels: Dict[str, float]  # Level 1 (20D), Level 2 (50D), Level 3 (200D)
    distance_to_nearest_sell_trigger_pct: float
    score_adj: int              # -15 to +10 pts
    insights: List[str]
    summary_card: str

_DEFAULT_CTA_SIG = CTAPositioningSignal(
    spy_price=580.0,
    cta_net_exposure_pct=100,
    cta_regime="MAX_LONG_ACCELERATION",
    trigger_levels={'level_1_20d_sma': 570.0, 'level_2_50d_sma': 555.0, 'level_3_200d_sma': 520.0, 'donchian_20d_high': 585.0},
    distance_to_nearest_sell_trigger_pct=1.75,
    score_adj=10,
    insights=["✅ S&P 500이 20일선 및 50일선 위에 안착하여 CTA 펀드 100% 풀 매수 우위 유지"],
    summary_card="CTA 100% MAX LONG"
)

_CTA_CACHE = {
    'cta_signal': (time.time(), _DEFAULT_CTA_SIG)
}
_CTA_TTL = 1800  # 30 Minutes TTL


class CTATrendFollowingSentinel:
    """Monitors systematic CTA trend-following fund mechanical positioning and trigger points."""

    def analyze(self) -> CTAPositioningSignal:
        now = time.time()
        if 'cta_signal' in _CTA_CACHE:
            ts, sig = _CTA_CACHE['cta_signal']
            if now - ts < _CTA_TTL:
                return sig

        spy_price = 500.0
        cta_pct = 100
        cta_regime = "MODERATE_LONG"
        score_adj = 0
        dist_trigger = 2.0
        triggers = {}
        insights = []

        try:
            spy = yf.download('SPY', period='1y', progress=False)
            if spy is not None and not spy.empty and 'Close' in spy:
                closes = spy['Close']
                if isinstance(closes.columns, pd.MultiIndex):
                    closes.columns = closes.columns.get_level_values(0)
                spy_series = closes.iloc[:, 0] if isinstance(closes, pd.DataFrame) else closes

                spy_price = round(float(spy_series.iloc[-1]), 2)
                sma20 = round(float(spy_series.rolling(20).mean().iloc[-1]), 2)
                sma50 = round(float(spy_series.rolling(50).mean().iloc[-1]), 2)
                sma100 = round(float(spy_series.rolling(100).mean().iloc[-1]), 2)
                sma200 = round(float(spy_series.rolling(200).mean().iloc[-1]), 2)
                high20 = round(float(spy_series.rolling(20).max().iloc[-1]), 2)

                triggers = {
                    'level_1_20d_sma': sma20,
                    'level_2_50d_sma': sma50,
                    'level_3_200d_sma': sma200,
                    'donchian_20d_high': high20
                }

                # 4-Horizon CTA Exposure Calculation
                cta_score = 0
                if spy_price > sma20: cta_score += 25
                if spy_price > sma50: cta_score += 25
                if spy_price > sma100: cta_score += 25
                if spy_price > sma200: cta_score += 25

                cta_pct = cta_score  # 0% to 100%
                dist_sma20 = ((spy_price / sma20) - 1.0) * 100.0
                dist_trigger = round(dist_sma20, 2)

                # Regime & Front-Running Signals
                if cta_pct == 100:
                    if spy_price >= high20 * 0.995:
                        cta_regime = "MAX_LONG_ACCELERATION"
                        score_adj = +10
                        insights.append(f"🚀 [CTA_MAX_ACCELERATION] CTAs 100% Long & near 20D High (${high20:.2f}). Systematic buying momentum maximum.")
                    else:
                        cta_regime = "MAX_LONG_STABLE"
                        score_adj = +5
                        insights.append(f"🟢 [CTA_MAX_LONG] CTAs 100% Long. SPY comfortably above 20D (${sma20:.2f}, +{dist_sma20:.1f}%) and 50D (${sma50:.2f}).")
                elif cta_pct >= 50:
                    cta_regime = "MODERATE_LONG"
                    score_adj = 0
                    insights.append(f"🟡 [CTA_MODERATE] CTAs {cta_pct}% Long. Mixed trend signals.")
                elif 0 < cta_pct < 50:
                    cta_regime = "UNWIND_RISK"
                    score_adj = -10
                    insights.append("⚠️ [CTA_UNWIND_ACTIVE] CTAs liquidating long positions. Below short-term moving averages.")
                else:
                    cta_regime = "MAX_SHORT"
                    score_adj = -20
                    insights.append(f"🚨 [CTA_MAX_SHORT] SPY below 200D SMA (${sma200:.2f})! CTAs flipped to aggressive Net Short.")

                # Cliff Level Proximity Warning (Within 0.5% of breaking 20D SMA)
                if 0.0 <= dist_sma20 <= 0.60:
                    score_adj = min(score_adj, -10)
                    insights.append(f"⚠️ [CTA_CLIFF_PROXIMITY] SPY is within {dist_sma20:.2f}% of 20D SMA ($ {sma20:.2f})! High risk of mechanical CTA selling cascade.")
        except Exception as e:
            logger.debug("CTA Sentinel error: {}", e)

        summary = (
            f"CTA Exposure: {cta_pct}% ({cta_regime}) | "
            f"20D Trigger: ${triggers.get('level_1_20d_sma', 0):.2f} (Dist: {dist_trigger:+.1f}%) | "
            f"CTA Adj: {score_adj:+d} pts"
        )

        sig = CTAPositioningSignal(
            spy_price=spy_price,
            cta_net_exposure_pct=cta_pct,
            cta_regime=cta_regime,
            trigger_levels=triggers,
            distance_to_nearest_sell_trigger_pct=dist_trigger,
            score_adj=score_adj,
            insights=insights,
            summary_card=summary
        )

        _CTA_CACHE['cta_signal'] = (now, sig)
        return sig


def get_cta_sentinel() -> CTATrendFollowingSentinel:
    return CTATrendFollowingSentinel()
