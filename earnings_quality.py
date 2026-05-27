"""
Earnings Quality Scorer
========================
Measures the quality of reported earnings by comparing:
- Free Cash Flow vs Net Income (accruals = low quality)
- Operating Cash Flow Margin
- Return on Invested Capital

High-quality earnings → sustainable, not manipulated
Low-quality earnings → red flag, potential earnings miss ahead

Scoring:
- FCF > Net Income → +20 (cash-backed earnings)
- FCF << Net Income → -20 (accrual-based, unsustainable)
- High ROE + low debt → +15
"""
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger
from typing import Dict, Any

try:
    from base_analyzer import BaseAnalyzer
except ImportError:
    class BaseAnalyzer:
        category = "fundamental"
        name = "base"
        def analyze(self, df, **kwargs): pass


class EarningsQualityScorer(BaseAnalyzer):
    """Measures earnings quality via FCF vs net income and return metrics."""

    category = "fundamental"
    name = "Earnings Quality"
    is_symbol_dependent = True

    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        symbol = kwargs.get("symbol", "AAPL")
        score = 0
        signals = []

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info if hasattr(ticker, "info") else {}

            if not info:
                return {"score": 0, "signals": ["EARNINGS_QUALITY_NO_DATA"], "name": self.name}

            # 1. Free Cash Flow vs Market Cap (FCF yield)
            fcf = info.get("freeCashflow", 0) or 0
            market_cap = info.get("marketCap", 1) or 1
            net_income = info.get("netIncomeToCommon", 0) or 0

            if fcf > 0 and net_income > 0:
                fcf_ratio = fcf / net_income
                if fcf_ratio > 0.9:
                    score += 20
                    signals.append(f"HIGH_EARNINGS_QUALITY:FCF/NI={fcf_ratio:.1f}")
                elif fcf_ratio > 0.6:
                    score += 10
                    signals.append(f"DECENT_EARNINGS_QUALITY:FCF/NI={fcf_ratio:.1f}")
                elif fcf_ratio < 0.3:
                    score -= 20
                    signals.append(f"LOW_EARNINGS_QUALITY:FCF/NI={fcf_ratio:.1f}")
            elif fcf > 0 and net_income <= 0:
                # Cash generative despite net loss (e.g., Amazon early days)
                score += 15
                signals.append("FCF_POSITIVE_DESPITE_LOSS")
            elif fcf < 0 and net_income > 0:
                score -= 25
                signals.append("EARNINGS_NOT_CASH_BACKED")

            # 2. FCF Yield
            fcf_yield = fcf / market_cap if market_cap > 0 else 0
            if fcf_yield > 0.05:
                score += 15
                signals.append(f"STRONG_FCF_YIELD:{fcf_yield*100:.1f}%")
            elif fcf_yield > 0.02:
                score += 5
                signals.append(f"POSITIVE_FCF_YIELD:{fcf_yield*100:.1f}%")
            elif fcf_yield < 0:
                score -= 10
                signals.append(f"NEGATIVE_FCF_YIELD:{fcf_yield*100:.1f}%")

            # 3. Return on Equity
            roe = info.get("returnOnEquity", 0) or 0
            if roe > 0.20:
                score += 10
                signals.append(f"HIGH_ROE:{roe*100:.0f}%")
            elif roe < 0:
                score -= 10
                signals.append(f"NEGATIVE_ROE:{roe*100:.0f}%")

            # 4. Debt/Equity
            de = info.get("debtToEquity", 0) or 0
            if de > 200:
                score -= 10
                signals.append(f"HIGH_DEBT:{de:.0f}%")
            elif 0 < de < 50:
                score += 5
                signals.append(f"LOW_DEBT:{de:.0f}%")

        except Exception as e:
            logger.debug(f"EarningsQuality({symbol}): {e}")
            return {"score": 0, "signals": ["EARNINGS_QUALITY_ERROR"], "name": self.name}

        return {
            "score": max(-50, min(50, score)),
            "signals": signals,
            "name": self.name,
        }
