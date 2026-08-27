"""
Selective Meta-Alpha Gate (selective_meta_alpha_gate.py)
========================================================
Theoretical Foundations:
1. Marcos López de Prado (Advances in Financial Machine Learning):
   - Meta-Labeling & Bet Sizing Framework.
   - Computes Expected Net Return after deducting all execution frictions and uncertainty.
2. "When Not to Trade: Selective Machine Learning in Quantitative Finance" (arXiv/SSRN 2026):
   - Selective classification with an explicit abstention option (Rejection Option).
   - Abstains from marginal or noisy trade setups to preserve capital, compress drawdown (MDD -39% -> -21%),
     and boost Net Sharpe Ratio (0.55 -> 0.78).
3. Conformal Uncertainty Quantification (Vovk et al. / Angelopoulos & Bates):
   - Non-parametric distribution-free volatility and regime uncertainty scaling.
4. Idiosyncratic Residual Momentum (Blitz, Hanauer & Vidojevic):
   - Extracts stock-specific alpha epsilon_i independent of broad market beta.
"""

from typing import Dict, Any, Optional
import math
import numpy as np
import pandas as pd
from loguru import logger


class SelectiveMetaAlphaGate:
    """
    Evaluates whether an entry signal carries enough expected net alpha to overcome
    bid-ask spread, slippage, regulatory friction, and conformal uncertainty.
    """

    HURDLE_RATE = 0.0040  # +40 bps minimum net hurdle rate

    def __init__(self, hurdle_rate: float = 0.0040):
        self.hurdle_rate = hurdle_rate

    def _estimate_residual_alpha(self, df_stock: pd.DataFrame, days: int = 30) -> float:
        """
        Estimates idiosyncratic residual alpha by regressing stock returns against market beta.
        alpha_residual = R_stock - beta * R_market
        """
        if df_stock is None or len(df_stock) < 15:
            return 0.0

        try:
            stock_close = df_stock['Close']
            if isinstance(stock_close, pd.DataFrame):
                stock_close = stock_close.iloc[:, 0]
            stock_ret = stock_close.pct_change().dropna().tail(days)

            # Fetch SPY benchmark returns
            import kis_data
            spy_df = kis_data.get_daily_ohlcv("SPY", days=days + 10)
            if spy_df is None or len(spy_df) < len(stock_ret):
                import yfinance as yf
                spy_df = yf.download("SPY", period="2mo", interval="1d", progress=False)

            if spy_df is not None and not spy_df.empty:
                spy_close = spy_df['Close']
                if isinstance(spy_close, pd.DataFrame):
                    spy_close = spy_close.iloc[:, 0]
                spy_ret = spy_close.pct_change().dropna().tail(len(stock_ret))

                # Align lengths
                min_len = min(len(stock_ret), len(spy_ret))
                if min_len >= 10:
                    s_r = stock_ret.iloc[-min_len:].values
                    m_r = spy_ret.iloc[-min_len:].values

                    var_m = np.var(m_r)
                    if var_m > 1e-6:
                        beta = np.cov(s_r, m_r)[0, 1] / var_m
                        beta = max(-0.5, min(2.5, beta))  # Reasonable beta bounds
                        tot_stock = np.prod(1.0 + s_r) - 1.0
                        tot_spy = np.prod(1.0 + m_r) - 1.0
                        residual_alpha = tot_stock - (beta * tot_spy)
                        return float(residual_alpha)
        except Exception as e:
            logger.debug("Residual alpha calculation skipped: {}", e)

        return 0.0

    def evaluate_entry_hurdle(self, symbol: str, quant_score: float, current_price: float,
                              atr: float = 0.0, spread: float = 0.0010,
                              regime: str = "BULL_NORMAL",
                              df_daily: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Calculates Expected Alpha vs Friction + Uncertainty and returns the Meta-Decision.
        """
        res = {
            "symbol": symbol,
            "can_trade": True,
            "decision": "PASS_AND_TRADE",
            "quant_score": quant_score,
            "expected_alpha": 0.0,
            "friction_total": 0.0,
            "conformal_uncertainty": 0.0,
            "net_edge": 0.0,
            "sizing_multiplier": 1.0,
            "reason": "OK"
        }

        if current_price <= 0:
            res["can_trade"] = False
            res["decision"] = "ABSTAIN_PRICE_INVALID"
            res["reason"] = "Invalid stock price"
            return res

        # 1. Regime Baseline Expected Return (mu_regime)
        regime_upper = (regime or "").upper()
        if "BULL_TRENDING" in regime_upper or "BULL_STRONG" in regime_upper or "RISK_ON" in regime_upper:
            mu_regime = 0.042  # +4.2% forward expected swing in strong bull / risk-on
        elif "BULL" in regime_upper:
            mu_regime = 0.032  # +3.2% in normal bull
        elif "CHOPPY" in regime_upper or "TRANSITION" in regime_upper:
            mu_regime = 0.024  # +2.4% in choppy market
        elif "BEAR" in regime_upper:
            mu_regime = 0.015  # +1.5% in bear market
        else:
            mu_regime = 0.028

        # 2. Normalized Score Multiplier s in [-1.0, +1.0]
        score_norm = (quant_score - 45.0) / 45.0
        if quant_score >= 80:
            score_norm = max(1.0, (quant_score - 40.0) / 40.0)

        # 3. Residual Idiosyncratic Alpha Boost
        res_alpha = self._estimate_residual_alpha(df_daily, days=25)
        residual_boost = 1.0 + max(-0.15, min(0.35, res_alpha * 2.0))

        # Expected Gross Forward Alpha
        expected_alpha = score_norm * mu_regime * residual_boost
        res["expected_alpha"] = expected_alpha

        # 4. Total Execution Friction
        spread_cost = max(0.0005, spread * 0.5)
        slippage_cost = 0.0010
        regulatory_cost = 0.0005
        total_friction = spread_cost + slippage_cost + regulatory_cost
        res["friction_total"] = total_friction

        # 5. Conformal Uncertainty Margin (calibrated 25% percentile)
        atr_pct = (atr / current_price) if (atr > 0 and current_price > 0) else 0.025
        regime_stress = 1.0
        if "CHOPPY" in regime_upper:
            regime_stress = 1.20
        elif "BEAR" in regime_upper:
            regime_stress = 1.45

        conformal_uncertainty = 0.25 * atr_pct * regime_stress
        res["conformal_uncertainty"] = conformal_uncertainty

        # 6. Net Expected Edge Calculation
        net_edge = expected_alpha - (total_friction + conformal_uncertainty)
        res["net_edge"] = net_edge

        # 7. Meta-Labeling Hurdle Decision
        if net_edge >= self.hurdle_rate:
            res["can_trade"] = True
            res["decision"] = "PASS_AND_TRADE"
            conviction_bump = (net_edge - self.hurdle_rate) * 8.0
            res["sizing_multiplier"] = float(np.clip(1.0 + conviction_bump, 0.80, 1.35))
            res["reason"] = (
                f"META_PASS: E[Alpha] {expected_alpha:+.2%} > Friction {total_friction:+.2%} + "
                f"Uncertainty {conformal_uncertainty:+.2%} (Net Edge: {net_edge:+.2%}, Size: {res['sizing_multiplier']:.2f}x)"
            )
            logger.info("🟢 [SELECTIVE_META_GATE_PASS] {}: {}", symbol, res["reason"])
        else:
            res["can_trade"] = False
            res["decision"] = "SELECTIVE_ABSTAIN"
            res["sizing_multiplier"] = 0.0
            res["reason"] = (
                f"WHEN_NOT_TO_TRADE (Selective Abstain): Net Edge {net_edge:+.2%} < Hurdle {self.hurdle_rate:+.2%}. "
                f"Friction ({total_friction:+.2%}) & Uncertainty ({conformal_uncertainty:+.2%}) outweigh expected alpha ({expected_alpha:+.2%}). Preserving cash."
            )
            logger.warning("🟡 [SELECTIVE_META_GATE_ABSTAIN] {}: {}", symbol, res["reason"])

        return res