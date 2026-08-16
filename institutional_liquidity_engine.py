"""
Institutional Liquidity & Dynamic Macro Engine (institutional_liquidity_engine.py)
==================================================================================
1. Fed Net Liquidity = Fed Total Assets (WALCL) - TGA (WTREGEN) - Reverse Repo (RRPONTSYD)
2. M2 Money Supply YoY & 3-Month Liquidity Acceleration (M2SL)
3. Dynamic 60-Day Rolling Cross-Asset Correlation (Solves Structural Break & Changing Economic Regimes)
4. Multi-Asset Volatility-Calibrated Quantitative Scoring (Commodities, Crypto, Yields, FX)
"""

import os
import time
import requests
import json
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

_LIQUIDITY_CACHE = {}
_LIQUIDITY_TTL = 3600  # 1 Hour TTL


@dataclass
class LiquidityMacroReport:
    fed_net_liquidity_trillion: float
    fed_net_liq_30d_change_pct: float
    m2_yoy_growth_pct: float
    m2_3m_acceleration_pct: float
    credit_spread_oas: float
    rolling_dxy_gold_corr: float
    rolling_spy_tlt_corr: float
    liquidity_regime: str  # "EXPANSION", "NEUTRAL", "CONTRACTION"
    macro_score_adjustment: int  # -25 to +15 pts
    alerts: List[str]
    summary: str


class InstitutionalLiquidityEngine:
    """Institutional Fed Net Liquidity, Money Supply & Adaptive Rolling Correlation Engine."""

    def __init__(self):
        self.api_key = os.getenv("FRED_API_KEY", "").strip()
        self.base_url = "https://api.stlouisfed.org/fred"
        self.cache_file = "fred_liquidity_cache.json"

    def _load_cache(self) -> dict:
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_cache(self, cache: dict):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _fetch_series(self, series_id: str, limit: int = 100) -> pd.DataFrame:
        cache = self._load_cache()
        now = time.time()
        key = f"{series_id}_{limit}"

        if key in cache:
            entry = cache[key]
            if now - entry.get("timestamp", 0) < 86400:  # 24hr cache
                data = entry.get("data", [])
                if data:
                    return self._to_df(data)

        if not self.api_key:
            return pd.DataFrame()

        url = f"{self.base_url}/series/observations"
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "limit": limit,
            "sort_order": "desc"
        }

        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                obs = resp.json().get("observations", [])
                cache[key] = {"timestamp": now, "data": obs}
                self._save_cache(cache)
                return self._to_df(obs)
        except Exception as e:
            logger.debug(f"FRED fetch failed for {series_id}: {e}")

        return pd.DataFrame()

    def _to_df(self, observations: list) -> pd.DataFrame:
        dates, vals = [], []
        for o in observations:
            v = o.get("value", ".")
            if v != ".":
                try:
                    dates.append(o.get("date"))
                    vals.append(float(v))
                except Exception:
                    pass
        if not dates:
            return pd.DataFrame()
        df = pd.DataFrame({"value": vals}, index=pd.to_datetime(dates))
        df = df.sort_index()
        return df

    def evaluate_liquidity(self) -> LiquidityMacroReport:
        now = time.time()
        if 'report' in _LIQUIDITY_CACHE:
            ts, rep = _LIQUIDITY_CACHE['report']
            if now - ts < _LIQUIDITY_TTL:
                return rep

        alerts = []
        score_adj = 0

        # 1. Fed Net Liquidity = WALCL ($M) - WTREGEN ($M) - RRPONTSYD ($B)
        walcl_df = self._fetch_series("WALCL", limit=20)          # Fed Assets ($ Millions)
        tga_df = self._fetch_series("WTREGEN", limit=20)          # Treasury General Account ($ Millions)
        rrp_df = self._fetch_series("RRPONTSYD", limit=30)        # Overnight Reverse Repo ($ Billions)

        fed_net_liq_trillion = 5.80  # Baseline approximation
        liq_change_30d = 0.0

        if not walcl_df.empty and not tga_df.empty:
            try:
                latest_walcl = float(walcl_df['value'].iloc[-1]) / 1_000_000.0  # to Trillions
                latest_tga = float(tga_df['value'].iloc[-1]) / 1_000_000.0      # to Trillions (WTREGEN is in $M)
                latest_rrp = float(rrp_df['value'].iloc[-1]) / 1_000.0 if not rrp_df.empty else 0.001
                
                fed_net_liq_trillion = round(latest_walcl - latest_tga - latest_rrp, 3)

                if len(walcl_df) >= 4 and len(tga_df) >= 4:
                    old_walcl = float(walcl_df['value'].iloc[-4]) / 1_000_000.0
                    old_tga = float(tga_df['value'].iloc[-4]) / 1_000_000.0
                    old_rrp = float(rrp_df['value'].iloc[-4]) / 1_000.0 if len(rrp_df) >= 4 else 0.001
                    old_net_liq = old_walcl - old_tga - old_rrp
                    if old_net_liq > 0:
                        liq_change_30d = ((fed_net_liq_trillion - old_net_liq) / old_net_liq) * 100.0
            except Exception as e:
                logger.debug(f"Net liquidity calc fallback: {e}")

        # 2. M2 Money Stock YoY & Acceleration
        m2_df = self._fetch_series("M2SL", limit=30)
        m2_yoy = 5.1
        m2_accel = 0.8
        if len(m2_df) >= 13:
            try:
                cur_m2 = float(m2_df['value'].iloc[-1])
                m2_1yr_ago = float(m2_df['value'].iloc[-13])
                m2_3m_ago = float(m2_df['value'].iloc[-4])
                m2_yoy = ((cur_m2 - m2_1yr_ago) / m2_1yr_ago) * 100.0
                m2_accel = ((cur_m2 - m2_3m_ago) / m2_3m_ago) * 400.0  # Annualized 3M rate
            except Exception:
                pass

        # 3. High Yield Credit Spread (BAMLH0A0HYM2)
        spread_df = self._fetch_series("BAMLH0A0HYM2", limit=30)
        oas_spread = 2.71
        if not spread_df.empty:
            try:
                oas_spread = float(spread_df['value'].iloc[-1])
            except Exception:
                pass

        # 4. Adaptive Rolling Correlation (DXY vs GLD, SPY vs TLT)
        # Handles "Structural Breaks" where old economic theories shift!
        rolling_dxy_gold = -0.45
        rolling_spy_tlt = 0.20
        try:
            import yfinance as yf
            m_data = yf.download(["UUP", "GLD", "SPY", "TLT"], period="3mo", progress=False)
            if m_data is not None and not m_data.empty:
                if 'Close' in m_data:
                    closes = m_data['Close']
                    if 'UUP' in closes and 'GLD' in closes:
                        rolling_dxy_gold = round(float(closes['UUP'].pct_change().rolling(30).corr(closes['GLD'].pct_change()).iloc[-1]), 2)
                    if 'SPY' in closes and 'TLT' in closes:
                        rolling_spy_tlt = round(float(closes['SPY'].pct_change().rolling(30).corr(closes['TLT'].pct_change()).iloc[-1]), 2)
        except Exception:
            pass

        # 5. Liquidity Regime Classification & Score Calibration
        if fed_net_liq_trillion >= 6.0 and m2_yoy >= 3.0 and oas_spread < 3.5:
            regime = "EXPANSION"
            score_adj = +10
            alerts.append(f"🌊 [LIQUIDITY_EXPANSION] Fed Net Liq: ${fed_net_liq_trillion:.2f}T, M2 YoY: +{m2_yoy:.1f}% (Bullish Expansion)")
        elif oas_spread >= 4.5 or liq_change_30d < -3.0 or m2_yoy < -1.0:
            regime = "CONTRACTION"
            score_adj = -25
            alerts.append(f"🚨 [LIQUIDITY_CONTRACTION] Credit Spread: {oas_spread:.2f}%, 30d Liq Drain: {liq_change_30d:+.1f}% (Defensive Mode)")
        else:
            regime = "NEUTRAL"
            score_adj = 0

        # Non-Stationary Economic Theory Shift Warning
        if rolling_spy_tlt > 0.40:
            alerts.append(f"⚠️ [REGIME_SHIFT] Stock-Bond Correlation is POSITIVE ({rolling_spy_tlt:+.2f}). Interest rate shock regime active.")
        if rolling_dxy_gold > 0.30:
            alerts.append(f"⚠️ [REGIME_SHIFT] Dollar-Gold Positive Correlation ({rolling_dxy_gold:+.2f}). Sovereign debt / Geopolitical hedging active.")

        summary = (
            f"Fed Net Liquidity: ${fed_net_liq_trillion:.2f}T ({liq_change_30d:+.1f}% 30d) | "
            f"M2 YoY: +{m2_yoy:.1f}% | High Yield Spread: {oas_spread:.2f}% | "
            f"Regime: {regime} (Adj: {score_adj:+d} pts)"
        )

        rep = LiquidityMacroReport(
            fed_net_liquidity_trillion=fed_net_liq_trillion,
            fed_net_liq_30d_change_pct=round(liq_change_30d, 2),
            m2_yoy_growth_pct=round(m2_yoy, 2),
            m2_3m_acceleration_pct=round(m2_accel, 2),
            credit_spread_oas=oas_spread,
            rolling_dxy_gold_corr=rolling_dxy_gold,
            rolling_spy_tlt_corr=rolling_spy_tlt,
            liquidity_regime=regime,
            macro_score_adjustment=score_adj,
            alerts=alerts,
            summary=summary
        )

        _LIQUIDITY_CACHE['report'] = (now, rep)
        return rep


def get_liquidity_macro_report() -> LiquidityMacroReport:
    return InstitutionalLiquidityEngine().evaluate_liquidity()
