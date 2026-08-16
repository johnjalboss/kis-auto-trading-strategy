"""
VIX Regime Scaler (vix_regime_scaler.py)
========================================
Dynamically scales stop loss and trailing exit ATR multipliers based on macro market volatility (VIX):
- VIX < 16 (Low Volatility / Bull Melt-Up): Multiplier 1.6x (Tight profit lock, minimal giveback)
- 16 <= VIX <= 24 (Normal Volatility): Multiplier 2.0x (Standard institutional buffer)
- VIX > 24 (Elevated Volatility / Choppy Market): Multiplier 2.4x (Wide runway, avoids whipsaw shakes)
"""

from typing import Dict, Any
from loguru import logger
import kis_data

class VIXRegimeScaler:
    """Dynamic Volatility Stop & Exit Multiplier Calibrator"""

    def __init__(self):
        self._cached_vix = None

    def get_current_vix(self) -> float:
        """Fetches latest VIX value"""
        try:
            df = kis_data.get_daily_ohlcv("^VIX", days=5)
            if df is None or df.empty:
                df = kis_data.get_daily_ohlcv("VIX", days=5)
            if df is not None and not df.empty:
                val = float(df['Close'].iloc[-1])
                if val > 0:
                    self._cached_vix = val
                    return val
        except Exception:
            pass
        return self._cached_vix or 18.0

    def calculate_atr_multiplier(self, base_multiplier: float = 2.0) -> Dict[str, Any]:
        """Calculates optimal ATR multiplier scaled by market VIX"""
        vix = self.get_current_vix()
        
        if vix < 16.0:
            scale = 0.80  # 1.6x for base 2.0
            mode = "LOW_VOL_TIGHT"
        elif vix > 24.0:
            scale = 1.20  # 2.4x for base 2.0
            mode = "HIGH_VOL_WIDE"
        else:
            scale = 1.00  # 2.0x for base 2.0
            mode = "NORMAL_VOL"

        effective_mult = round(base_multiplier * scale, 2)
        logger.debug("📊 [VIX_SCALER] VIX: {:.1f} | Mode: {} | Effective ATR Mult: {:.2f}x (Base: {:.1f}x)",
                     vix, mode, effective_mult, base_multiplier)

        return {
            "vix": vix,
            "mode": mode,
            "scale": scale,
            "effective_multiplier": effective_mult
        }

def get_vix_regime_scaler() -> VIXRegimeScaler:
    return VIXRegimeScaler()
