"""
FX Risk Module - USD/KRW Exchange Rate Impact
===============================================
Monitors the USD/KRW exchange rate trend to gauge FX headwind/tailwind
for Korean investors holding US stocks.

Scoring:
- Strong USD (KRW weakening) → +20 (US stock gains amplified in KRW terms)
- Rapid KRW strengthening → -20 (US stock gains eroded when converted to KRW)
- Stable rate → neutral
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
        category = "macro"
        name = "base"
        def analyze(self, df, **kwargs): pass


class FXRiskAnalyzer(BaseAnalyzer):
    """USD/KRW exchange rate risk for Korean investors in US equities."""

    category = "macro"
    name = "FX Risk (USD/KRW)"
    is_symbol_dependent = False

    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        score = 0
        signals = []

        try:
            fx = yf.download("KRW=X", period="3mo", progress=False, auto_adjust=True)
            if isinstance(fx.columns, pd.MultiIndex):
                fx.columns = fx.columns.get_level_values(0)

            if fx.empty or len(fx) < 20:
                return {"score": 0, "signals": ["FX_DATA_UNAVAILABLE"], "name": self.name}

            close = fx["Close"].dropna()
            current = float(close.iloc[-1])     # USD/KRW rate
            ma20 = float(close.rolling(20).mean().iloc[-1])
            ma60 = float(close.rolling(min(60, len(close))).mean().iloc[-1])

            # 1-month change
            change_1m = (current - float(close.iloc[-21])) / float(close.iloc[-21]) * 100 if len(close) > 21 else 0

            # USD strength = KRW weakening (rate goes UP)
            if current > ma20 > ma60:
                score += 15
                signals.append(f"USD_STRONG:{current:.0f}")
            elif current < ma20 < ma60:
                score -= 15
                signals.append(f"USD_WEAK:{current:.0f}")

            # Rapid move in last month
            if change_1m > 3.0:
                score += 10
                signals.append(f"KRW_WEAKENING_FAST:{change_1m:.1f}%")
            elif change_1m < -3.0:
                score -= 10
                signals.append(f"KRW_STRENGTHENING_FAST:{change_1m:.1f}%")
            else:
                signals.append(f"FX_STABLE:{change_1m:.1f}%")

        except Exception as e:
            logger.debug(f"FXRisk: {e}")
            return {"score": 0, "signals": ["FX_DATA_ERROR"], "name": self.name}

        return {
            "score": max(-40, min(40, score)),
            "signals": signals,
            "name": self.name,
        }
