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
import config
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger
from typing import Dict, Any
import threading
import time
import concurrent.futures

# Global caches to prevent thundering herd and duplicate downloads
_sector_returns_cache = {}
_sector_returns_cache_time = 0.0
_sector_returns_lock = threading.Lock()

_symbol_sector_cache = {}
_symbol_sector_cache_lock = threading.Lock()

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

        global _sector_returns_cache, _sector_returns_cache_time
        global _symbol_sector_cache

        try:
            # 1. Get sector flows (5d momentum of each sector ETF) with global cache & lock
            sector_returns = {}
            need_fetch = False
            
            with _sector_returns_lock:
                now = time.time()
                # Cache valid for 15 minutes (900 seconds) to capture real-time intraday sector rotation
                if now - _sector_returns_cache_time < 900 and _sector_returns_cache:
                    sector_returns = _sector_returns_cache.copy()
                else:
                    need_fetch = True
                    
            if need_fetch:
                with _sector_returns_lock:
                    now = time.time()
                    # Recheck inside lock
                    if now - _sector_returns_cache_time < 900 and _sector_returns_cache:
                        sector_returns = _sector_returns_cache.copy()
                    else:
                        temp_returns = {}
                        def _fetch_etf(etf, sector):
                            try:
                                data = yf.download(etf, period="1mo", progress=False, auto_adjust=True)
                                if isinstance(data.columns, pd.MultiIndex):
                                    data.columns = data.columns.get_level_values(0)
                                if data.empty or len(data) < 5:
                                    return None
                                close = data["Close"].dropna()
                                ret_5d = (close.iloc[-1] / close.iloc[-5] - 1) * 100
                                ret_1m = (close.iloc[-1] / close.iloc[0] - 1) * 100
                                return sector, ret_5d * 0.7 + ret_1m * 0.3
                            except Exception:
                                return None

                        # Parallel fetch across 11 sector ETFs
                        with concurrent.futures.ThreadPoolExecutor(max_workers=11) as executor:
                            futures = [executor.submit(_fetch_etf, etf, sector) for etf, sector in self.SECTOR_ETFS.items()]
                            for fut in concurrent.futures.as_completed(futures):
                                res = fut.result()
                                if res:
                                    s_name, val = res
                                    temp_returns[s_name] = val
                                    
                        if temp_returns:
                            _sector_returns_cache = temp_returns.copy()
                            _sector_returns_cache_time = now
                            sector_returns = temp_returns.copy()
                            logger.info("SectorFundFlow: Updated global sector returns cache.")

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

            # 3. Get stock's sector with cache (sector never changes, so cache indefinitely)
            stock_sector = ""
            with _symbol_sector_cache_lock:
                stock_sector = _symbol_sector_cache.get(symbol, "")
                
            if not stock_sector:
                try:
                    # yfinance info call is made outside the lock to prevent serializing parallel threads
                    ticker = yf.Ticker(symbol)
                    info = ticker.info if hasattr(ticker, "info") else {}
                    yf_sector = info.get("sector", "")
                    stock_sector = self.SECTOR_MAP.get(yf_sector, "")
                    if stock_sector:
                        with _symbol_sector_cache_lock:
                            _symbol_sector_cache[symbol] = stock_sector
                        logger.info(f"SectorFundFlow: Cached sector '{stock_sector}' for {symbol}")
                except Exception as e:
                    logger.debug(f"SectorFundFlow({symbol}): Failed to fetch sector info: {e}")
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
