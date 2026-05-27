"""
Sector Fund Flow Monitor
=========================
Tracks real-time capital rotation between market sectors using ETF price
momentum to identify where institutional money is currently flowing.

Unlike etf_flows.py (which tracks aggregated ETF flow data), this module
compares ALL 11 GICS sector ETFs to find the current "hot money" sectors
and generate buy/sell signals based on where the target stock fits.

Scoring:
- Stock's sector is in top 3 fund flows → +25 (follow the money)
- Stock's sector is in bottom 3 outflows → -25
- Neutral sectors → 0
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
        is_symbol_dependent = True
        def analyze(self, df, **kwargs): pass


class SectorFundFlow(BaseAnalyzer):
    """Monitors real-time capital rotation across all 11 market sectors."""

    category = "macro"
    name = "Sector Fund Flow"
    is_symbol_dependent = True

    # All 11 GICS sector ETFs + sector mapping
    SECTOR_ETFS = {
        "XLK": "Technology",
        "XLF": "Financials",
        "XLV": "Healthcare",
        "XLC": "Communication",
        "XLY": "Consumer Discretionary",
        "XLP": "Consumer Staples",
        "XLI": "Industrials",
        "XLE": "Energy",
        "XLU": "Utilities",
        "XLRE": "Real Estate",
        "XLB": "Materials",
    }

    # Map yfinance sector strings → our ETF sectors
    SECTOR_MAP = {
        "Technology": "Technology",
        "Financial Services": "Financials",
        "Healthcare": "Healthcare",
        "Communication Services": "Communication",
        "Consumer Cyclical": "Consumer Discretionary",
        "Consumer Defensive": "Consumer Staples",
        "Industrials": "Industrials",
        "Energy": "Energy",
        "Utilities": "Utilities",
        "Real Estate": "Real Estate",
        "Basic Materials": "Materials",
    }

    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        symbol = kwargs.get("symbol", "AAPL")
        score = 0
        signals = []

        try:
            # 1. Get sector flows (5d momentum of each sector ETF)
            sector_returns = {}
            for etf, sector in self.SECTOR_ETFS.items():
                try:
                    data = yf.download(etf, period="1mo", progress=False, auto_adjust=True)
                    if isinstance(data.columns, pd.MultiIndex):
                        data.columns = data.columns.get_level_values(0)
                    if data.empty or len(data) < 5:
                        continue
                    close = data["Close"].dropna()
                    ret_5d = (close.iloc[-1] / close.iloc[-5] - 1) * 100
                    ret_1m = (close.iloc[-1] / close.iloc[0] - 1) * 100
                    # Composite: 70% recent (5d) + 30% monthly
                    sector_returns[sector] = ret_5d * 0.7 + ret_1m * 0.3
                except Exception:
                    continue

            if not sector_returns:
                return {"score": 0, "signals": ["SECTOR_FLOW_NO_DATA"], "name": self.name}

            # 2. Rank sectors by inflow
            sorted_sectors = sorted(sector_returns.items(), key=lambda x: x[1], reverse=True)
            top3 = [s[0] for s in sorted_sectors[:3]]
            bottom3 = [s[0] for s in sorted_sectors[-3:]]
            best_sector = sorted_sectors[0]
            worst_sector = sorted_sectors[-1]

            signals.append(f"TOP_INFLOW:{best_sector[0]}({best_sector[1]:+.1f}%)")
            signals.append(f"TOP_OUTFLOW:{worst_sector[0]}({worst_sector[1]:+.1f}%)")

            # 3. Get stock's sector
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info if hasattr(ticker, "info") else {}
                yf_sector = info.get("sector", "")
                stock_sector = self.SECTOR_MAP.get(yf_sector, "")
            except Exception:
                stock_sector = ""

            # 4. Score based on sector positioning
            if stock_sector:
                if stock_sector in top3:
                    rank = top3.index(stock_sector)
                    sector_score = 25 - rank * 5  # 25, 20, 15
                    score += sector_score
                    signals.append(f"IN_HOT_SECTOR:{stock_sector}(rank#{rank+1})")
                elif stock_sector in bottom3:
                    rank = bottom3.index(stock_sector)
                    sector_score = -(25 - rank * 5)  # -25, -20, -15
                    score += sector_score
                    signals.append(f"IN_COLD_SECTOR:{stock_sector}")
                else:
                    sector_ret = sector_returns.get(stock_sector, 0)
                    signals.append(f"NEUTRAL_SECTOR:{stock_sector}({sector_ret:+.1f}%)")
            else:
                signals.append("SECTOR_UNKNOWN")

        except Exception as e:
            logger.debug(f"SectorFundFlow({symbol}): {e}")
            return {"score": 0, "signals": ["SECTOR_FLOW_ERROR"], "name": self.name}

        return {
            "score": max(-30, min(30, score)),
            "signals": signals,
            "name": self.name,
        }
