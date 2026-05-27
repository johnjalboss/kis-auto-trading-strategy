"""
Economic Surprise Index
========================
Tracks economic indicator surprises (actual vs. consensus forecast).
Based on key US macro indicators that move markets:

- PMI (Manufacturing & Services)
- Consumer Confidence
- Jobs (NFP vs estimate)
- CPI vs expectations

Uses yfinance ETF proxies since direct economic data isn't always available:
- TIP (TIPS ETF) = inflation surprise proxy
- HYG (High Yield) = risk appetite / credit health
- TLT (Long Bonds) = growth/recession expectations
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


class EconomicSurpriseAnalyzer(BaseAnalyzer):
    """Measures economic surprise via macro ETF momentum proxies."""

    category = "macro"
    name = "Economic Surprise Index"
    is_symbol_dependent = False

    # Proxy ETFs for economic health
    PROXIES = {
        "HYG": ("Credit Risk Appetite", 1),    # High yield ETF — risk on/off
        "TIP": ("Inflation Expectations", -1),  # TIPS — high = inflation hurting stocks
        "TLT": ("Long Bond", -1),               # Long bonds — falling = growth
        "XLI": ("Industrial Activity", 1),      # Industrials = economic activity
        "XLF": ("Financial Health", 1),         # Financials = credit/growth
    }

    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        score = 0
        signals = []

        try:
            for ticker_sym, (label, direction) in self.PROXIES.items():
                try:
                    data = yf.download(ticker_sym, period="1mo", progress=False, auto_adjust=True)
                    if isinstance(data.columns, pd.MultiIndex):
                        data.columns = data.columns.get_level_values(0)
                    if data.empty or len(data) < 5:
                        continue

                    close = data["Close"].dropna()
                    ret_1m = (close.iloc[-1] / close.iloc[0] - 1) * 100
                    ret_5d = (close.iloc[-1] / close.iloc[-5] - 1) * 100 if len(close) >= 5 else 0

                    # Score based on direction and recent momentum
                    momentum = ret_5d * direction
                    if momentum > 1.5:
                        score += 8
                        signals.append(f"{label}:POSITIVE")
                    elif momentum < -1.5:
                        score -= 8
                        signals.append(f"{label}:NEGATIVE")

                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"EconomicSurprise: {e}")
            return {"score": 0, "signals": ["ECON_SURPRISE_ERROR"], "name": self.name}

        return {
            "score": max(-40, min(40, score)),
            "signals": signals if signals else ["ECON_NEUTRAL"],
            "name": self.name,
        }
