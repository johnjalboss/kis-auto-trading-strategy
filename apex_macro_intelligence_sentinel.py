"""
Apex Macro Intelligence Sentinel (apex_macro_intelligence_sentinel.py)
========================================================================
Wall Street Tier-1 Alternative Cross-Market Macro & Credit Radar:

1. 🏗️ Dr. Copper / Gold Real Growth Ratio (CPER / GLD)
   - Real global manufacturing & AI data-center buildout demand vs safe-haven fear.
2. 💳 Corporate Credit Appetite (HYG / LQD)
   - High-Yield Junk Bonds vs Investment-Grade Bonds (Credit risk appetite).
3. 🏦 Systemic Banking Liquidity Health (KBE / SPY)
   - Regional Bank stability vs Broad Market (SVB-style banking stress early warning).
4. 🌊 Treasury Bond Volatility & Risk-Parity Deleveraging (TLT Realized Vol)
   - Detects violent bond market swings that trigger multi-billion dollar Risk-Parity equity dumps.
"""

import time
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger

_APEX_MACRO_CACHE = {}
_APEX_MACRO_TTL = 1800  # 30 Minutes TTL


@dataclass
class ApexMacroSignal:
    copper_gold_ratio: float
    copper_gold_trend: str        # "GROWTH_EXPANSION", "NEUTRAL", "FEAR_CONTRACTION"
    credit_appetite_ratio: float  # HYG / LQD
    credit_appetite_trend: str    # "RISK_SEEKING", "NEUTRAL", "CREDIT_FLIGHT_TO_QUALITY"
    banking_health_ratio: float   # KBE / SPY
    banking_stress: bool
    bond_volatility_pct: float    # 10-day realized volatility of TLT
    risk_parity_deleveraging_risk: bool
    score_adjustment: int         # -25 to +15 pts
    alerts: List[str]
    summary: str


class ApexMacroIntelligenceSentinel:
    """Alternative Cross-Market Macro & Credit Health Sentinel."""

    TICKERS = ['CPER', 'GLD', 'HYG', 'LQD', 'KBE', 'SPY', 'TLT']

    def analyze(self) -> ApexMacroSignal:
        now = time.time()
        if 'signal' in _APEX_MACRO_CACHE:
            ts, sig = _APEX_MACRO_CACHE['signal']
            if now - ts < _APEX_MACRO_TTL:
                return sig

        data = {}
        for t in self.TICKERS:
            try:
                df = yf.download(t, period='1mo', progress=False)
                if df is not None and not df.empty:
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    data[t] = df['Close']
            except Exception as e:
                logger.debug(f"Apex ticker fetch error for {t}: {e}")

        alerts = []
        score_adj = 0

        # 1. Dr. Copper / Gold Real Growth Ratio (CPER / GLD)
        cg_ratio = 0.16
        cg_trend = "NEUTRAL"
        if 'CPER' in data and 'GLD' in data and len(data['CPER']) >= 5 and len(data['GLD']) >= 5:
            try:
                c_now = float(data['CPER'].iloc[-1])
                g_now = float(data['GLD'].iloc[-1])
                c_5d = float(data['CPER'].iloc[-5])
                g_5d = float(data['GLD'].iloc[-5])
                
                cg_ratio = round(c_now / g_now, 4) if g_now > 0 else 0.16
                cg_5d_ret = ((c_now / g_now) / (c_5d / g_5d) - 1.0) * 100.0

                if cg_5d_ret > 1.5:
                    cg_trend = "GROWTH_EXPANSION"
                    score_adj += 5
                    alerts.append(f"🏗️ [DR_COPPER_GROWTH] Copper/Gold ratio rising (+{cg_5d_ret:.1f}% 5d). Real economic & capex demand strong.")
                elif cg_5d_ret < -2.0:
                    cg_trend = "FEAR_CONTRACTION"
                    score_adj -= 10
                    alerts.append(f"⚠️ [STAGFLATION_FEAR] Gold outperforming Copper ({cg_5d_ret:.1f}% 5d). Defensive safe-haven rotation.")
            except Exception:
                pass

        # 2. Corporate Credit Appetite (HYG / LQD)
        credit_ratio = 0.70
        credit_trend = "NEUTRAL"
        if 'HYG' in data and 'LQD' in data and len(data['HYG']) >= 5 and len(data['LQD']) >= 5:
            try:
                hyg_now = float(data['HYG'].iloc[-1])
                lqd_now = float(data['LQD'].iloc[-1])
                hyg_5d = float(data['HYG'].iloc[-5])
                lqd_5d = float(data['LQD'].iloc[-5])

                credit_ratio = round(hyg_now / lqd_now, 4) if lqd_now > 0 else 0.70
                credit_5d_ret = ((hyg_now / lqd_now) / (hyg_5d / lqd_5d) - 1.0) * 100.0

                if credit_5d_ret > 0.8:
                    credit_trend = "RISK_SEEKING"
                    score_adj += 5
                    alerts.append("💳 [CREDIT_RISK_ON] Junk bonds outperforming IG bonds. Corporate credit appetite high.")
                elif credit_5d_ret < -1.2:
                    credit_trend = "CREDIT_FLIGHT_TO_QUALITY"
                    score_adj -= 10
                    alerts.append("🚨 [CREDIT_STRESS] High Yield spreads widening vs Investment Grade. Credit risk-off.")
            except Exception:
                pass

        # 3. Systemic Banking Liquidity Health (KBE / SPY)
        bank_ratio = 0.08
        bank_stress = False
        if 'KBE' in data and 'SPY' in data and len(data['KBE']) >= 5 and len(data['SPY']) >= 5:
            try:
                kbe_now = float(data['KBE'].iloc[-1])
                spy_now = float(data['SPY'].iloc[-1])
                kbe_5d = float(data['KBE'].iloc[-5])
                spy_5d = float(data['SPY'].iloc[-5])

                bank_ratio = round(kbe_now / spy_now, 4) if spy_now > 0 else 0.08
                bank_5d_ret = ((kbe_now / spy_now) / (kbe_5d / spy_5d) - 1.0) * 100.0

                if bank_5d_ret < -4.0:
                    bank_stress = True
                    score_adj -= 15
                    alerts.append(f"🏦 [BANKING_STRESS_ALERT] Regional banks underperforming SPY by {bank_5d_ret:.1f}% in 5 days. Systemic caution.")
            except Exception:
                pass

        # 4. Treasury Bond Volatility & Risk-Parity Deleveraging
        bond_vol = 1.2
        rp_risk = False
        if 'TLT' in data and len(data['TLT']) >= 10:
            try:
                tlt_daily_rets = data['TLT'].pct_change().dropna()
                bond_vol = round(float(tlt_daily_rets.tail(10).std() * np.sqrt(252) * 100.0), 2)
                if bond_vol > 22.0:  # High bond volatility threshold
                    rp_risk = True
                    score_adj -= 10
                    alerts.append(f"🌊 [RISK_PARITY_DUMP_RISK] Treasury bond annualized volatility at {bond_vol:.1f}% (>22%). Multi-asset funds deleveraging.")
            except Exception:
                pass

        summary = (
            f"Copper/Gold: {cg_trend} (Ratio: {cg_ratio:.4f}) | "
            f"Credit: {credit_trend} (HYG/LQD: {credit_ratio:.4f}) | "
            f"Banking Stress: {'ALERT' if bank_stress else 'HEALTHY'} | "
            f"Bond Vol: {bond_vol:.1f}% | Apex Adj: {score_adj:+d} pts"
        )

        sig = ApexMacroSignal(
            copper_gold_ratio=cg_ratio,
            copper_gold_trend=cg_trend,
            credit_appetite_ratio=credit_ratio,
            credit_appetite_trend=credit_trend,
            banking_health_ratio=bank_ratio,
            banking_stress=bank_stress,
            bond_volatility_pct=bond_vol,
            risk_parity_deleveraging_risk=rp_risk,
            score_adjustment=score_adj,
            alerts=alerts,
            summary=summary
        )

        _APEX_MACRO_CACHE['signal'] = (now, sig)
        return sig


def get_apex_macro_intelligence_signal() -> ApexMacroSignal:
    return ApexMacroIntelligenceSentinel().analyze()
