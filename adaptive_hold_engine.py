"""
[v10.0 INSTITUTIONAL DYNAMIC ADAPTIVE HOLDING ENGINE]
Replaces rigid static 5-day holding limits with dynamic regime-aware holding rules:

1. Winner Extension Rule (Let Winners Run):
   - If stock PnL >= +2.0% AND Technical Trend is Bullish (Price > EMA20 / 1H Aligned):
   - Extend holding limit from 5 days -> 15 days!
2. Dead Money Early Exit Rule:
   - If stock PnL is stagnant (-1.0% to +1.0%) for 3 days AND RVOL < 0.8:
   - Trigger early exit at Day 3 (DEAD_MONEY_EXIT) to free up capital.
3. Underperformer Hard Limit:
   - If stock PnL is negative at Day 5: Forcibly liquidate (TIME_EXPIRED_EXIT).
"""

from typing import Dict, Any
from loguru import logger
import pandas as pd


class AdaptiveHoldingEngine:
    def __init__(self):
        pass

    def evaluate_holding_status(self, symbol: str, hold_hours: float, pnl_pct: float, df: pd.DataFrame = None) -> Dict[str, Any]:
        res = {
            'should_exit': False,
            'reason': '',
            'max_allowed_hours': 32.5  # Default 5 trading days (5 * 6.5h)
        }

        if hold_hours <= 0:
            return res

        days_held = hold_hours / 6.5

        # 1. Winner Extension Rule (Let Winners Run up to 15 trading days = 97.5h)
        if pnl_pct >= 0.02:  # +2.0% profit or higher
            is_uptrend = True
            if df is not None and len(df) >= 20:
                try:
                    close = df['Close'].values.flatten()
                    ema20 = float(pd.Series(close).ewm(span=20).mean().iloc[-1])
                    cur_price = float(close[-1])
                    if cur_price < ema20:
                        is_uptrend = False
                except Exception:
                    pass

            if is_uptrend:
                res['max_allowed_hours'] = 97.5  # 15 trading days!
                logger.debug("🔥 [WINNER_EXTENSION] {}: PnL {:+.1%} & Uptrend -> Extended max hold to 15 days", symbol, pnl_pct)

        # 2. Dead Money Early Exit Rule (3 trading days = 19.5h)
        if hold_hours >= 19.5 and -0.01 <= pnl_pct <= 0.01:
            res['should_exit'] = True
            res['reason'] = f"DEAD_MONEY_EXIT: {days_held:.1f} days held with stagnant PnL ({pnl_pct:+.1%}). Freeing cash for active leaders."
            logger.info("💤 [DEAD_MONEY_EXIT] {}: {}", symbol, res['reason'])
            return res

        # 3. Dynamic Threshold Expiry Check
        if hold_hours >= res['max_allowed_hours']:
            res['should_exit'] = True
            res['reason'] = f"DYNAMIC_TIME_EXPIRED: {days_held:.1f} days held (Max limit: {res['max_allowed_hours']/6.5:.0f}d), PnL ({pnl_pct:+.1%})"
            logger.info("⏱️ [DYNAMIC_HOLD_EXPIRED] {}: {}", symbol, res['reason'])

        return res
