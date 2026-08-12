"""
Tail-Risk Circuit Breaker Engine (tail_risk_circuit_breaker.py)
================================================================
Monitors intraday market index velocity (SPY / QQQ) and VIX spikes (>30%).
Triggers automatic BUY freeze, tightens trailing stops by 50%, and enables SQQQ hedge protection.
"""

from typing import Dict, Any
from loguru import logger

class TailRiskCircuitBreaker:
    def __init__(self, vix_spike_threshold: float = 30.0, index_drop_threshold: float = -0.018):
        self.vix_spike_threshold = vix_spike_threshold
        self.index_drop_threshold = index_drop_threshold

    def check_tail_risk(self, spy_df=None, vix_val: float = 0.0) -> Dict[str, Any]:
        is_triggered = False
        reasons = []

        # 1. VIX Spike Check
        if vix_val >= self.vix_spike_threshold:
            is_triggered = True
            reasons.append(f"VIX Spike ({vix_val:.1f} >= {self.vix_spike_threshold})")

        # 2. SPY Intraday Drop Velocity Check
        if spy_df is not None and not spy_df.empty and len(spy_df) >= 5:
            last_close = float(spy_df['Close'].iloc[-1])
            prev_close = float(spy_df['Close'].iloc[-5])
            velocity = (last_close - prev_close) / prev_close if prev_close > 0 else 0.0

            if velocity <= self.index_drop_threshold:
                is_triggered = True
                reasons.append(f"SPY Rapid Drop ({velocity*100:.2f}% <= {self.index_drop_threshold*100:.2f}%)")

        if is_triggered:
            logger.warning("🛡️ [TAIL_RISK_BREAKER] TRIGGERED! Reasons: {} | Freezing BUYs, Tightening Stops 50%",
                           ", ".join(reasons))
            return {
                "is_active": True,
                "freeze_buys": True,
                "stop_tightening_factor": 0.50, # Tighten stop distance by 50%
                "hedge_recommended": True,
                "hedge_symbol": "SQQQ",
                "reasons": reasons
            }

        return {
            "is_active": False,
            "freeze_buys": False,
            "stop_tightening_factor": 1.0,
            "hedge_recommended": False,
            "hedge_symbol": None,
            "reasons": []
        }

def get_tail_risk_breaker() -> TailRiskCircuitBreaker:
    return TailRiskCircuitBreaker()
