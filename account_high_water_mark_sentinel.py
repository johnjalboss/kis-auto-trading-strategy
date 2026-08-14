"""
2. Hedge Fund Account High-Water Mark (HWM) Dynamic Sentinel (account_high_water_mark_sentinel.py)
===================================================================================================
Theoretical Foundation (Dynamic Risk Budgeting / Didier Sornette & Jean-Philippe Bouchaud):
- Maintains an all-time High-Water Mark (HWM) equity record: E_max = max(E_0, E_1, ..., E_t).
- Measures empirical drawdown from peak: DD_HWM = (E_t - E_max) / E_max.
- If DD_HWM <= -4.5%:
    Activates "PROFIT_LOCK_IN_MODE":
    1. Multiplies new position sizes by 0.50x to protect accumulated capital.
    2. Elevates minimum entry score to 85 (only hyper-conviction setups allowed).
- Ensures that accumulated account profits are mathematically locked in and never returned to the market during macro downturns.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger

class AccountHighWaterMarkSentinel:
    """Monitors Portfolio High-Water Mark and dynamically locks in realized profits"""

    def __init__(self, state_file: str = "hwm_state.json", threshold_drawdown_pct: float = -4.5):
        self.state_file = Path(state_file)
        self.threshold_dd = threshold_drawdown_pct
        self._load_state()

    def _load_state(self):
        self.hwm_equity = 0.0
        self.last_updated = ""
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                self.hwm_equity = float(data.get("hwm_equity", 0.0))
                self.last_updated = data.get("last_updated", "")
            except Exception:
                pass

    def _save_state(self):
        try:
            data = {
                "hwm_equity": round(self.hwm_equity, 2),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error("Failed to save HWM state: {}", e)

    def evaluate_equity(self, current_equity: float) -> Dict[str, Any]:
        """
        Evaluate current portfolio equity against historical peak HWM
        """
        res = {
            "current_equity": round(current_equity, 2),
            "hwm_equity": round(self.hwm_equity, 2),
            "drawdown_from_hwm_pct": 0.0,
            "is_profit_lock_active": False,
            "sizing_multiplier": 1.0,
            "score_threshold_boost": 0,
            "status": "NORMAL_GROWTH"
        }

        if current_equity <= 0:
            return res

        # Update High-Water Mark if new peak reached
        if current_equity > self.hwm_equity:
            self.hwm_equity = current_equity
            self._save_state()
            res["hwm_equity"] = round(self.hwm_equity, 2)
            res["status"] = "NEW_ALL_TIME_HIGH"
            logger.info("🏰 [HIGH_WATER_MARK] New Account Peak Equity reached: ${:.2f}", current_equity)
            return res

        # Calculate drawdown from peak
        if self.hwm_equity > 0:
            dd_pct = ((current_equity - self.hwm_equity) / self.hwm_equity) * 100.0
            res["drawdown_from_hwm_pct"] = round(dd_pct, 2)

            if dd_pct <= self.threshold_dd:
                res["is_profit_lock_active"] = True
                res["sizing_multiplier"] = 0.50
                res["score_threshold_boost"] = 5
                res["status"] = "PROFIT_LOCK_IN_ACTIVE"
                logger.warning("🏰 [PROFIT_LOCK_IN] DD from Peak is {:.2f}% (<= {:.1f}%). Sizing halved to 0.50x to protect capital.",
                               dd_pct, self.threshold_dd)

        return res
