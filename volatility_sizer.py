"""
3. Volatility-Targeted Position Sizer (volatility_sizer.py)
===========================================================
Dynamically scales position sizing inversely to Parkinson Realized Volatility.
Keeps portfolio risk constant across changing market regimes.
Zero-Distortion Data Integrity: Calculates exact high/low range Parkinson volatility.
"""

import pandas as pd
import numpy as np
import math
from loguru import logger

class VolatilityTargetedSizer:
    """Parkinson Realized Volatility Sizer"""
    
    def __init__(self, target_volatility: float = 0.15):
        self.target_volatility = target_volatility
        
    def calculate_parkinson_volatility(self, df: pd.DataFrame, period: int = 20) -> float:
        """Calculate Parkinson High-Low Realized Volatility"""
        if df is None or df.empty or len(df) < period or 'High' not in df.columns or 'Low' not in df.columns:
            return 0.20  # fallback standard volatility (20%)
            
        try:
            high = df['High'].values[-period:]
            low = df['Low'].values[-period:]
            
            # Avoid divide by zero
            valid_mask = (low > 0) & (high >= low)
            if not np.any(valid_mask):
                return 0.20
                
            log_hl = np.log(high[valid_mask] / low[valid_mask])
            parkinson_sq = (log_hl ** 2) / (4 * math.log(2))
            annualized_vol = math.sqrt(np.mean(parkinson_sq) * 252)
            return max(0.05, float(annualized_vol))
        except Exception as e:
            logger.debug("Parkinson Volatility calc error: {}", e)
            return 0.20

    def get_volatility_multiplier(self, df: pd.DataFrame) -> float:
        """Calculate position sizing multiplier based on realized volatility"""
        realized_vol = self.calculate_parkinson_volatility(df)
        mult = self.target_volatility / realized_vol
        # Clamp multiplier between 0.5x and 1.5x to prevent extreme sizing distortion
        clamped_mult = max(0.5, min(1.5, mult))
        return clamped_mult
