"""
Safe Math Utilities (safe_math.py)
==================================
Provides zero-division safe calculation wrappers for all quant indicators and portfolio math.
"""

from typing import Union
import pandas as pd
import numpy as np

def safe_div(numerator: Union[float, int, pd.Series], 
             denominator: Union[float, int, pd.Series], 
             fallback: float = 0.0) -> Union[float, pd.Series]:
    """
    Safely divides numerator by denominator. Returns fallback if denominator is 0, NaN, or None.
    """
    if isinstance(denominator, (pd.Series, np.ndarray)):
        res = numerator / denominator.replace(0, np.nan)
        return res.fillna(fallback)

    if denominator is None or denominator == 0 or pd.isna(denominator):
        return fallback

    try:
        res = numerator / denominator
        return fallback if pd.isna(res) or np.isinf(res) else res
    except Exception:
        return fallback
