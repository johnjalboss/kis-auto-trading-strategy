"""
Cross-Asset Tail Risk Sentinel (cross_asset_tail_sentinel.py)
============================================================
Real-time macro multi-asset liquidity and tail-risk monitor:
- 10-Year Treasury Yield (^TNX) rate shock
- High-Yield Credit Spread Shock (HYG / LQD ratio collapse)
- US Dollar Index Spike (UUP)
- VIX Term Structure Inversion (^VIX > ^VIX3M)
When systemic liquidity shocks are detected, triggers instant freeze on new long entries.
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
import time
from loguru import logger

_sentinel_cache = {
    "stress_score": 0,
    "risk_label": "NORMAL (정상)",
    "freeze_entries": False,
    "triggers": [],
    "cached_at": "INIT"
}
_sentinel_cache_time = time.time()
SENTINEL_CACHE_TTL = 900  # 15 min cache


class CrossAssetTailRiskSentinel:
    """Monitors cross-asset macroeconomic tail risk and market liquidity."""

    def __init__(self):
        pass

    def _fetch_history(self, symbol: str, days: int = 15) -> Optional[pd.DataFrame]:
        # Skip KIS for index symbols (^TNX, ^VIX)
        if not symbol.startswith("^"):
            try:
                import kis_data as kd
                df = kd.get_daily_ohlcv(symbol, days=days)
                if df is not None and len(df) >= 5:
                    return df
            except Exception:
                pass

        try:
            import yfinance as yf
            df = yf.download(symbol, period="1mo", interval="1d", progress=False, auto_adjust=True)
            if df is not None and len(df) >= 2:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                return df
        except Exception:
            pass
        return None

    def evaluate_tail_risk(self) -> Dict[str, Any]:
        """Evaluates macro cross-asset stress indicators with 15-min cache."""
        global _sentinel_cache, _sentinel_cache_time
        now = time.time()
        if _sentinel_cache is not None and (now - _sentinel_cache_time < SENTINEL_CACHE_TTL):
            return _sentinel_cache.copy()

        triggers = []
        stress_score = 0

        # 1. 10-Year Treasury Yield Shock (^TNX)
        try:
            tnx_df = self._fetch_history("^TNX", days=10)
            if tnx_df is not None and len(tnx_df) >= 2:
                tnx_curr = float(tnx_df['Close'].iloc[-1])
                tnx_prev = float(tnx_df['Close'].iloc[-2])
                tnx_chg_pct = (tnx_curr - tnx_prev) / tnx_prev if tnx_prev > 0 else 0.0
                if tnx_chg_pct >= 0.040:  # +4.0% daily yield spike
                    triggers.append(f"YIELD_SHOCK: 10Y Yield spiked {tnx_chg_pct:+.1%}")
                    stress_score += 35
        except Exception as e:
            logger.debug("TNX tail check error: {}", e)

        # 2. Credit Spread Stress (HYG / LQD Ratio)
        try:
            hyg_df = self._fetch_history("HYG", days=10)
            lqd_df = self._fetch_history("LQD", days=10)
            if hyg_df is not None and lqd_df is not None and len(hyg_df) >= 2 and len(lqd_df) >= 2:
                hyg_ret = float(hyg_df['Close'].iloc[-1] / hyg_df['Close'].iloc[-2] - 1)
                lqd_ret = float(lqd_df['Close'].iloc[-1] / lqd_df['Close'].iloc[-2] - 1)
                spread_delta = hyg_ret - lqd_ret
                if spread_delta <= -0.012:  # High-Yield underperforming IG bonds by > 1.2%
                    triggers.append(f"CREDIT_SPREAD_BLOWOUT: High-Yield lagged IG by {spread_delta:+.2%}")
                    stress_score += 40
        except Exception as e:
            logger.debug("Credit spread tail check error: {}", e)

        # 3. Dollar Liquidity Squeeze (UUP)
        try:
            uup_df = self._fetch_history("UUP", days=10)
            if uup_df is not None and len(uup_df) >= 2:
                uup_chg = float(uup_df['Close'].iloc[-1] / uup_df['Close'].iloc[-2] - 1)
                if uup_chg >= 0.012:  # +1.2% daily dollar spike
                    triggers.append(f"DOLLAR_SQUEEZE: UUP spiked {uup_chg:+.2%}")
                    stress_score += 25
        except Exception as e:
            logger.debug("Dollar squeeze tail check error: {}", e)

        # 4. VIX Term Structure Inversion (^VIX vs ^VIX3M)
        try:
            vix_df = self._fetch_history("^VIX", days=5)
            vix3m_df = self._fetch_history("^VIX3M", days=5)
            if vix_df is not None and vix3m_df is not None:
                vix_val = float(vix_df['Close'].iloc[-1])
                vix3m_val = float(vix3m_df['Close'].iloc[-1])
                if vix_val > vix3m_val and vix_val >= 22.0:
                    triggers.append(f"VIX_INVERSION: VIX ({vix_val:.1f}) > VIX3M ({vix3m_val:.1f})")
                    stress_score += 45
        except Exception as e:
            logger.debug("VIX inversion tail check error: {}", e)

        is_tail_risk = (stress_score >= 50) or (len(triggers) >= 2)
        freeze_entries = is_tail_risk

        res = {
            "is_tail_risk": is_tail_risk,
            "freeze_entries": freeze_entries,
            "stress_score": stress_score,
            "triggers": triggers,
            "risk_label": "HIGH_SYSTEMIC_TAIL_RISK" if is_tail_risk else "NORMAL_CROSS_ASSET_FLOW"
        }

        _sentinel_cache = res.copy()
        _sentinel_cache_time = now
        return res
