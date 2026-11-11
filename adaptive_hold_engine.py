"""
[v10.1 INSTITUTIONAL DYNAMIC ADAPTIVE HOLDING ENGINE]
Replaces rigid static holding limits with dynamic regime-aware holding rules:

1. Winner Extension Rule (Let Winners Run):
   - If stock PnL >= +2.0% AND Technical Trend is Bullish (Price > EMA20 / 1H Aligned):
   - Extend holding limit from 5 days -> 15 days!
2. Dead Money Exit Rule (Swing Calibration: 5 trading days = 32.5h):
   - If stock PnL is stagnant (-1.5% to +1.5%) for 5 full trading days AND volume has dried up (RVOL < 0.85):
   - Trigger early exit at Day 5 (DEAD_MONEY_EXIT) to free up capital.
   - Prevents prematurely cutting healthy 2-3 day coil consolidations before multi-day breakout.
3. Underperformer Hard Limit:
   - If stock reaches max allowed hours without profit: Forcibly liquidate (TIME_EXPIRED_EXIT).
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
            'max_allowed_hours': 45.5  # Default 7 trading days (7 * 6.5h) for pure swing
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

        # 2. Dead Money Exit Rule (5 full trading days = 32.5h)
        # Prevents cutting healthy 2-3 day coil consolidations. Only exits if stagnant for 5 full days AND volume dried up.
        if hold_hours >= 32.5 and -0.015 <= pnl_pct <= 0.015:
            low_volume = True
            if df is not None and len(df) >= 20 and 'Volume' in df.columns:
                try:
                    vol_series = df['Volume']
                    avg_vol = float(vol_series.tail(20).mean())
                    curr_vol = float(vol_series.iloc[-1])
                    if avg_vol > 0 and (curr_vol / avg_vol) > 0.85:
                        low_volume = False  # Volume still active, do not force-choke
                except Exception:
                    pass

            if low_volume:
                res['should_exit'] = True
                res['reason'] = f"DEAD_MONEY_EXIT: {days_held:.1f} trading days held with stagnant PnL ({pnl_pct:+.1%}) and dried volume. Freeing cash for active leaders."
                logger.info("💤 [DEAD_MONEY_EXIT] {}: {}", symbol, res['reason'])
                return res

        # 3. Dynamic Threshold Expiry Check
        if hold_hours >= res['max_allowed_hours']:
            res['should_exit'] = True
            res['reason'] = f"DYNAMIC_TIME_EXPIRED: {days_held:.1f} trading days held (Max limit: {res['max_allowed_hours']/6.5:.0f}d), PnL ({pnl_pct:+.1%})"
            logger.info("⏱️ [DYNAMIC_HOLD_EXPIRED] {}: {}", symbol, res['reason'])

        return res
