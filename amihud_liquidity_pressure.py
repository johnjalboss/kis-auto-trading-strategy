"""
Amihud Illiquidity & Institutional Flow Pressure Engine (amihud_liquidity_pressure.py)
======================================================================================
Implements Amihud (2002) Illiquidity Ratio and Price Impact Efficiency (PIE)
to detect institutional accumulation footprint before major momentum breakouts:
- High Upward PIE (Z > +1.5σ) : Institutional price-push efficiency (stealth accumulation)
- High Downward PIE (Z < -1.5σ) : Fragile liquidity dump (avoid entry)
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
from loguru import logger


class AmihudLiquidityPressureEngine:
    """Calculates Amihud Price Impact Efficiency and Institutional Accumulation Pressure."""

    def analyze(self, df: Optional[pd.DataFrame], symbol: str = "") -> Dict[str, Any]:
        default_res = {
            "symbol": symbol,
            "amihud_illiq": 0.0,
            "pie_zscore": 0.0,
            "is_institutional_accumulation": False,
            "is_fragile_liquidity": False,
            "score_bonus": 0,
            "flow_label": "NEUTRAL_FLOW"
        }

        if df is None or len(df) < 20:
            return default_res

        try:
            close = df['Close']
            volume = df['Volume']
            high = df['High'] if 'High' in df else close
            low = df['Low'] if 'Low' in df else close

            # Returns and Dollar Volume (in millions)
            returns = close.pct_change().fillna(0.0)
            dollar_vol = (close * volume) / 1e6  # $ Millions
            dollar_vol = dollar_vol.replace(0, np.nan).ffill().fillna(1.0)

            # Amihud Illiquidity Ratio: |R_t| / DollarVolume_t
            illiq_series = (returns.abs() / dollar_vol)
            
            # Directional Price Impact Efficiency: R_t / DollarVolume_t
            pie_series = (returns / dollar_vol)

            # 20-day rolling baseline
            rolling_mean = pie_series.rolling(20).mean()
            rolling_std = pie_series.rolling(20).std().replace(0, 1e-6)
            pie_zscore = float((pie_series.iloc[-1] - rolling_mean.iloc[-1]) / rolling_std.iloc[-1]) if len(rolling_std) >= 20 else 0.0

            current_illiq = float(illiq_series.iloc[-1]) if not illiq_series.empty else 0.0

            # Signal classification
            if pie_zscore >= 1.5:
                is_inst = True
                is_fragile = False
                score_bonus = 20 if pie_zscore >= 2.2 else 12
                flow_label = "INSTITUTIONAL_ACCUMULATION_SURGE"
            elif pie_zscore <= -1.5:
                is_inst = False
                is_fragile = True
                score_bonus = -15
                flow_label = "INSTITUTIONAL_DISTRIBUTION_PRESSURE"
            else:
                is_inst = False
                is_fragile = False
                score_bonus = 0
                flow_label = "NORMAL_LIQUIDITY_FLOW"

            return {
                "symbol": symbol,
                "amihud_illiq": round(current_illiq, 4),
                "pie_zscore": round(pie_zscore, 2),
                "is_institutional_accumulation": is_inst,
                "is_fragile_liquidity": is_fragile,
                "score_bonus": score_bonus,
                "flow_label": flow_label
            }
        except Exception as e:
            logger.debug("AmihudLiquidityPressureEngine failed for {}: {}", symbol, e)
            return default_res
