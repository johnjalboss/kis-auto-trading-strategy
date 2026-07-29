"""
Short Squeeze Monitor
======================
Detects potential short squeeze setups:
- High short interest + rising price momentum = squeeze candidate
- Uses short % of float + recent price action as proxy

Scoring:
- High short interest (>15%) + uptrend → strong bullish (squeeze potential)
- High short interest + downtrend → bearish (shorts winning)
- Low short interest → neutral
"""
import config
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger
from typing import Dict, Any

try:
    from base_analyzer import BaseAnalyzer
except ImportError:
    class BaseAnalyzer:
        category = "smart_money"
        name = "base"
        def analyze(self, df, **kwargs): pass


class ShortSqueezeMonitor(BaseAnalyzer):
    """Detects short squeeze setups via short interest + price momentum."""

    category = "smart_money"
    name = "Short Squeeze Monitor"
    is_symbol_dependent = True

    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        symbol = kwargs.get("symbol", "AAPL")
        score = 0
        signals = []

        try:
            import config
            ticker = yf.Ticker(symbol)
            info = ticker.info if hasattr(ticker, "info") else {}

            short_pct = info.get("shortPercentOfFloat", 0) or 0
            short_ratio = info.get("shortRatio", 0) or 0  # days to cover

            # Price momentum from df
            close = df["Close"] if "Close" in df.columns else pd.Series()
            if len(close) >= 10:
                ret_10d = (close.iloc[-1] / close.iloc[-10] - 1) * 100
                ret_5d = (close.iloc[-1] / close.iloc[-5] - 1) * 100
            else:
                ret_10d = ret_5d = 0

            # Short squeeze criteria
            if short_pct > 0.20:  # >20% short float
                if ret_5d > 3:
                    score += 35
                    signals.append(f"SQUEEZE_SETUP:short={short_pct*100:.0f}% price+{ret_5d:.1f}%")
                elif ret_10d > 5:
                    score += 25
                    signals.append(f"SQUEEZE_SIGNAL:short={short_pct*100:.0f}%")
                else:
                    score -= 10
                    signals.append(f"HIGH_SHORT_NO_SQUEEZE:{short_pct*100:.0f}%")
            elif short_pct > 0.10:  # 10-20%
                if ret_5d > 2:
                    score += 15
                    signals.append(f"MODERATE_SQUEEZE_POTENTIAL:{short_pct*100:.0f}%")
                else:
                    signals.append(f"MODERATE_SHORT:{short_pct*100:.0f}%")
            elif short_pct < 0.03:
                score += 5
                signals.append(f"LOW_SHORT_INTEREST:{short_pct*100:.0f}%")

            # Days to cover amplifies the signal
            if short_ratio > 5 and score > 0:
                score += 10
                signals.append(f"HIGH_DAYS_TO_COVER:{short_ratio:.1f}d")

        except Exception as e:
            logger.debug(f"ShortSqueeze({symbol}): {e}")
            return {"score": 0, "signals": ["SHORT_DATA_UNAVAILABLE"], "name": self.name}

        return {
            "score": max(-35, min(45, score)),
            "signals": signals,
            "name": self.name,
        }
