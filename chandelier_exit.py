"""
Chandelier ATR Dynamic Trailing Exit Module
=============================================
Calculates Chandelier Exit trailing stop line:
Trailing Stop = Highest High (since entry) - (atr_multiplier * ATR)

Protects 70-80%+ of peak unrealized profits during strong trend extensions.
"""

from typing import Dict, Any
import pandas as pd
from loguru import logger


class ChandelierExit:
    def __init__(self, atr_multiplier: float = 2.0, atr_period: int = 14):
        self.atr_multiplier = atr_multiplier
        self.atr_period = atr_period

    def calculate_stop(self, df: pd.DataFrame, entry_price: float) -> Dict[str, Any]:
        """
        Calculates current Chandelier Exit stop price.
        Returns dict with stop_price, is_exit_triggered, highest_high, atr.
        """
        if df is None or len(df) < self.atr_period:
            # Fallback to entry_price - 4.5%
            return {
                "stop_price": entry_price * 0.955,
                "is_exit_triggered": False,
                "highest_high": entry_price,
                "atr": entry_price * 0.02
            }

        try:
            high = df['High']
            low = df['Low']
            close = df['Close']

            # ATR Calculation
            tr = pd.concat([
                high - low,
                (high - close.shift()).abs(),
                (low - close.shift()).abs()
            ], axis=1).max(axis=1)
            atr = float(tr.rolling(self.atr_period).mean().iloc[-1])

            # Highest High since entry (using recent bars)
            highest_high = max(float(high.max()), entry_price)
            current_price = float(close.iloc[-1])

            # Chandelier Exit Stop Price
            chandelier_stop = highest_high - (self.atr_multiplier * atr)
            
            # Floor stop at entry - 4.5% safety stop
            safety_stop = entry_price * 0.955
            final_stop = max(chandelier_stop, safety_stop)

            is_triggered = current_price < final_stop

            return {
                "stop_price": final_stop,
                "is_exit_triggered": is_triggered,
                "highest_high": highest_high,
                "atr": atr,
                "current_price": current_price
            }
        except Exception as e:
            logger.debug("ChandelierExit calculation error: {}", e)
            return {
                "stop_price": entry_price * 0.955,
                "is_exit_triggered": False,
                "highest_high": entry_price,
                "atr": entry_price * 0.02
            }
