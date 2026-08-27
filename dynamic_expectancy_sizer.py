"""
5. Dynamic Expectancy-Linked Fractional Kelly Sizer (dynamic_expectancy_sizer.py)
================================================================================
Adjusts trade position sizing multiplier dynamically based on rolling 20-trade Expectancy:
- Empirical Expectancy: E = (WinRate * AvgWin) - ((1 - WinRate) * AvgLoss)
- Dynamic Scale Factor = clamp(0.50, 1.25, 1.0 + (E - Base_E) * 5.0)
- Compound returns aggressively during hot winning streaks, scale back safely during drawdowns.
"""

import os
import sqlite3
import pandas as pd
import numpy as np
from typing import Dict, Any
from loguru import logger

class DynamicExpectancySizer:
    """Calculates Dynamic Expectancy Scaling Factor for Position Sizing"""

    def __init__(self, db_path: str = "trades.db", base_expectancy: float = 0.02):
        self.db_path = db_path
        self.base_expectancy = base_expectancy

    def get_sizing_multiplier(self) -> Dict[str, Any]:
        """
        Calculates position sizing multiplier based on recent settled trades since 2026-08-14 clean slate.
        """
        res = {
            "multiplier": 1.0,
            "expectancy": 0.0,
            "win_rate": 0.5,
            "avg_win": 0.04,
            "avg_loss": 0.03,
            "trade_count": 0,
            "is_baseline": True,
            "label": "TRAILING_CYCLE_BASELINE (최근 30회 실거래 롤링 표본)"
        }

        if not os.path.exists(self.db_path):
            return res

        try:
            conn = sqlite3.connect(self.db_path)
            query = """
                SELECT pnl_pct FROM trades 
                WHERE side = 'SELL' AND pnl_pct IS NOT NULL AND pnl_pct != 0
                ORDER BY created_at DESC LIMIT 30
            """
            df = pd.read_sql_query(query, conn)
            conn.close()

            if df.empty or len(df) < 3:
                return res

            pnl_series = df['pnl_pct'].values / 100.0
            wins = pnl_series[pnl_series > 0]
            losses = np.abs(pnl_series[pnl_series < 0])

            n_total = len(pnl_series)
            win_rate = len(wins) / n_total
            avg_win = float(np.mean(wins)) if len(wins) > 0 else 0.04
            avg_loss = float(np.mean(losses)) if len(losses) > 0 else 0.03

            expectancy = (win_rate * avg_win) - ((1.0 - win_rate) * avg_loss)

            # Sizing multiplier scaled around base expectancy
            diff = expectancy - self.base_expectancy
            raw_mult = 1.0 + (diff * 8.0)
            mult = float(np.clip(raw_mult, 0.50, 1.25))

            res["multiplier"] = round(mult, 2)
            res["win_rate"] = round(float(win_rate), 2)
            res["avg_win"] = round(float(avg_win), 3)
            res["avg_loss"] = round(float(avg_loss), 3)
            res["expectancy"] = round(float(expectancy), 4)
            res["sample_trades"] = n_total

            if mult >= 1.15:
                res["label"] = "HIGH_EXPECTANCY_EXPANSION"
            elif mult <= 0.70:
                res["label"] = "LOW_EXPECTANCY_CONTRACTION"

            return res

        except Exception as e:
            logger.debug("Dynamic expectancy sizer failed: {}", e)
            return res
