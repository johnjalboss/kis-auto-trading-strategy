"""
Estimate Revision Momentum Module
===================================
Tracks analyst earnings estimate revisions.
Upward revisions → strong buy signal (one of the most reliable predictors).

Scoring based on:
- Forward PE vs trailing PE trend (proxy for estimate revision)
- Earnings growth trajectory
- Revenue growth vs prior period
"""
import config
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger
from typing import Dict, Any

try:
    import config
    from base_analyzer import BaseAnalyzer
except ImportError:
    class BaseAnalyzer:
        category = "fundamental"
        name = "base"
        def analyze(self, df, **kwargs): pass


class EstimateRevisionAnalyzer(BaseAnalyzer):
    """Analyst earnings estimate revision momentum."""

    category = "fundamental"
    name = "Estimate Revision Momentum"
    is_symbol_dependent = True

    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        symbol = kwargs.get("symbol", "AAPL")
        score = 0
        signals = []

        try:
            import config
            ticker = yf.Ticker(symbol)
            info = ticker.info if hasattr(ticker, "info") else {}

            if not info:
                return {"score": 0, "signals": ["ESTIMATE_DATA_UNAVAILABLE"], "name": self.name}

            # 1. Forward PE < Trailing PE → earnings expected to GROW
            fwd_pe = info.get("forwardPE", 0) or 0
            trail_pe = info.get("trailingPE", 0) or 0

            if fwd_pe > 0 and trail_pe > 0:
                ratio = trail_pe / fwd_pe
                if ratio > 1.15:
                    score += 20
                    signals.append(f"EARNINGS_GROWTH_EXPECTED:{ratio:.2f}x")
                elif ratio < 0.85:
                    score -= 20
                    signals.append(f"EARNINGS_DECLINE_EXPECTED:{ratio:.2f}x")

            # 2. Earnings Growth
            eg = info.get("earningsGrowth", 0) or 0
            if eg > 0.20:
                score += 15
                signals.append(f"STRONG_EARNINGS_GROWTH:{eg*100:.0f}%")
            elif eg > 0.05:
                score += 7
                signals.append(f"POSITIVE_EARNINGS_GROWTH:{eg*100:.0f}%")
            elif eg < -0.10:
                score -= 15
                signals.append(f"EARNINGS_DECLINING:{eg*100:.0f}%")

            # 3. Revenue Growth
            rg = info.get("revenueGrowth", 0) or 0
            if rg > 0.15:
                score += 10
                signals.append(f"STRONG_REVENUE_GROWTH:{rg*100:.0f}%")
            elif rg < -0.05:
                score -= 10
                signals.append(f"REVENUE_DECLINING:{rg*100:.0f}%")

            # 4. Recommendation trend
            rec = info.get("recommendationMean", 3.0) or 3.0
            if rec <= 1.8:
                score += 15
                signals.append(f"ANALYST_STRONG_BUY:{rec:.1f}")
            elif rec <= 2.3:
                score += 8
                signals.append(f"ANALYST_BUY:{rec:.1f}")
            elif rec >= 3.5:
                score -= 10
                signals.append(f"ANALYST_SELL:{rec:.1f}")

        except Exception as e:
            logger.debug(f"EstimateRevision({symbol}): {e}")
            return {"score": 0, "signals": ["ESTIMATE_ERROR"], "name": self.name}

        return {
            "score": max(-50, min(50, score)),
            "signals": signals,
            "name": self.name,
        }
