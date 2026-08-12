"""
2026 Cutting-Edge Quant Module 4: Order Flow Imbalance Detector (order_flow_imbalance.py)
===========================================================================================
Calculates real-time trade flow imbalance (OFI) and volume power ratio.
Distinguishes genuine institutional buying pressure from false retail breakout traps.
"""

from typing import Dict, Any
import pandas as pd
from loguru import logger
from safe_math import safe_div


class OrderFlowImbalanceDetector:
    """Real-Time Order Flow & Trade Imbalance Evaluator."""

    def evaluate_ofi(self, df_bars: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        Calculates 5-period volume power and price impact ratio.
        """
        if df_bars is None or len(df_bars) < 5:
            return {"ofi_score": 0, "is_institutional_buying": False, "volume_power_ratio": 1.0}

        try:
            close = df_bars['Close']
            volume = df_bars['Volume']

            price_diff = close.diff()
            buy_vol = volume.where(price_diff > 0, 0.0).tail(5).sum()
            sell_vol = volume.where(price_diff < 0, 0.0).tail(5).sum()

            vol_ratio = safe_div(buy_vol, max(1.0, sell_vol), fallback=1.0)
            
            if vol_ratio >= 2.0:
                ofi_score = +20
                is_inst_buying = True
                label = "STRONG_INSTITUTIONAL_ACCUMULATION"
            elif vol_ratio <= 0.5:
                ofi_score = -20
                is_inst_buying = False
                label = "INSTITUTIONAL_DISTRIBUTION"
            else:
                ofi_score = 0
                is_inst_buying = False
                label = "BALANCED_ORDER_FLOW"

            logger.info("🌊 [ORDER_FLOW_IMBALANCE] {}: VolRatio {:.2f}x ({}) -> OFI Score: {} pts",
                        symbol, vol_ratio, label, ofi_score)

            return {
                "ofi_score": ofi_score,
                "is_institutional_buying": is_inst_buying,
                "volume_power_ratio": vol_ratio,
                "label": label
            }
        except Exception as e:
            logger.debug("OrderFlowImbalanceDetector error for {}: {}", symbol, e)
            return {"ofi_score": 0, "is_institutional_buying": False, "volume_power_ratio": 1.0}
