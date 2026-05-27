"""
Statistical Arbitrage & Cointegration Engine
===========================================
Identifies temporary pricing spreads between historically correlated assets.
If AMD drops 3% but NVDA is flat, implies an impending mean-reversion snapback.
Automatically wrapped by the 130-Module Orchestrator.
"""

from base_analyzer import BaseAnalyzer
from loguru import logger
import pandas as pd
import numpy as np

import data_proxy
import yfinance as yf # Shimmed by data_proxy

class StatArbAdapter(BaseAnalyzer):
    def __init__(self):
        self._name = "StatArbPairs"
        self._category = "SMART_MONEY"
        
        # Define high-correlation pairs
        self.PAIRS = {
            "AMD": "NVDA",
            "GOOGL": "MSFT",
            "V": "MA",
            "HD": "LOW"
        }
        
    @property
    def name(self) -> str: return self._name
    
    @property
    def category(self) -> str: return self._category
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> dict:
        """Calculate Z-score of the spread between the target and its pair."""
        result = {'score': 0, 'signals': []}
        
        # Orchestrator usually passes the target symbol through kwargs if available, or we infer it
        target_symbol = kwargs.get('symbol', None)
        if not target_symbol or target_symbol not in self.PAIRS:
            return result
            
        pair_symbol = self.PAIRS[target_symbol]
        
        try:
            # Fetch recent pair data via the KIS API proxy
            pair_df = yf.download(pair_symbol, period='3mo', interval='1d', progress=False)
            
            if pair_df is None or len(pair_df) < 10 or len(df) < 10:
                return result
                
            # Create a localized series for comparison (Swing: 50 days)
            target_closes = df['Close'].tail(50).pct_change().dropna()
            pair_closes = pair_df['Close'].tail(50).pct_change().dropna()
            
            # Simple spread calculation for Swing Trading pairs
            spread = target_closes - pair_closes
            
            # Calculate Z-score of the most recent spread
            z_score = (spread.iloc[-1] - spread.mean()) / spread.std()
            
            # If Z-score < -2.0, target is artificially cheap compared to its peer
            if z_score < -2.0:
                result['score'] = 25  # Strong mean-reversion buy
                result['signals'].append(f"STAT_ARB: {target_symbol} deeply oversold vs {pair_symbol} (Z={z_score:.2f})")
            # If Z-score > 2.0, target is artificially expensive
            elif z_score > 2.0:
                result['score'] = -25 # Strong short / sell
                result['signals'].append(f"STAT_ARB: {target_symbol} overextended vs {pair_symbol} (Z={z_score:.2f})")
                
        except Exception as e:
            logger.debug(f"StatArb calculation skipped for {target_symbol}: {e}")
            
        return result
