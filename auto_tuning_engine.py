"""
World-Class Institutional Quant Auto-Tuning Engine (auto_tuning_engine.py)
========================================================================
Designed by World #1 Quant Systems Architecture.
Continuously analyzes real closed trade executions, win rate, profit factor,
expectancy, and market regime to autonomously optimize trading parameters:
  - MIN_ENTRY_SCORE (Entry strictness)
  - STOP_LOSS_PCT (Safety stop floor)
  - TAKE_PROFIT_PCT (Trailing profit target)
  - MAX_POSITION_PCT (Capital allocation per slot)
  - RVOL_MIN (Relative volume surge filter)
"""

import os, sqlite3, math, json
from datetime import datetime, date, timedelta
from loguru import logger

class AutoTuningEngine:
    """Institutional-Grade Self-Optimizing Quant Parameter Tuner"""
    
    def __init__(self, db_path: str = "trades.db"):
        self.db_path = db_path if os.path.exists(db_path) else "/home/ubuntu/kis-auto-trading/trades.db"
        self.config_override_file = "autotune_config.json"
        
    def _get_db_connection(self):
        if os.path.exists(self.db_path):
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        return None

    def analyze_performance(self, lookback_days: int = 30) -> dict:
        """Calculate deep quant performance metrics from real trades"""
        conn = self._get_db_connection()
        if not conn:
            return {}
            
        cur = conn.cursor()
        since_date = (date.today() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        
        cur.execute("""
            SELECT symbol, side, quantity, price, pnl, pnl_pct, reason, regime, created_at 
            FROM trades 
            WHERE side = 'SELL' AND created_at >= ?
            ORDER BY id ASC
        """, (since_date,))
        rows = cur.fetchall()
        conn.close()
        
        if not rows:
            return {
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "net_pnl": 0.0,
                "expectancy": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0
            }
            
        wins = [r['pnl'] for r in rows if r['pnl'] > 0]
        losses = [r['pnl'] for r in rows if r['pnl'] < 0]
        total_pnl = sum(r['pnl'] for r in rows)
        
        n_trades = len(rows)
        n_wins = len(wins)
        n_losses = len(losses)
        
        win_rate = (n_wins / n_trades * 100.0) if n_trades > 0 else 0.0
        gross_profit = sum(wins) if wins else 0.0
        gross_loss = abs(sum(losses)) if losses else 0.0
        
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 1.0)
        avg_win = (gross_profit / n_wins) if n_wins > 0 else 0.0
        avg_loss = (gross_loss / n_losses) if n_losses > 0 else 0.0
        expectancy = (total_pnl / n_trades) if n_trades > 0 else 0.0
        
        return {
            "total_trades": n_trades,
            "wins": n_wins,
            "losses": n_losses,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "net_pnl": total_pnl,
            "expectancy": expectancy,
            "avg_win": avg_win,
            "avg_loss": avg_loss
        }

    def run_autotune(self) -> dict:
        """
        Execute Institutional Auto-Tuning Logic:
        Dynamically adjusts entry threshold, stop loss, profit target, and position sizing.
        """
        metrics = self.analyze_performance(lookback_days=30)
        logger.info("🤖 AutoTuning Engine running analysis: {}", metrics)
        
        # Default Baseline Institutional Parameters
        tuned_params = {
            "MIN_ENTRY_SCORE": 80,
            "STOP_LOSS_PCT": 0.045,
            "TAKE_PROFIT_PCT": 0.090,
            "MAX_POSITION_PCT": 0.20,
            "RVOL_MIN": 1.5,
            "TUNED_AT": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "REASON": "Baseline Optimization"
        }
        
        n_trades = metrics.get("total_trades", 0)
        win_rate = metrics.get("win_rate", 0.0)
        pf = metrics.get("profit_factor", 1.0)
        
        if n_trades >= 5:
            # 1. Underperforming Regime (Win rate < 55% or Profit Factor < 1.3)
            # Tighten filters: Require higher score, higher relative volume, tighter stop loss
            if win_rate < 55.0 or pf < 1.3:
                tuned_params["MIN_ENTRY_SCORE"] = 85
                tuned_params["STOP_LOSS_PCT"] = 0.038
                tuned_params["RVOL_MIN"] = 2.0
                tuned_params["MAX_POSITION_PCT"] = 0.15
                tuned_params["REASON"] = f"DEFENSIVE TUNING: Low WinRate ({win_rate:.1f}%) / PF ({pf:.2f}) -> Tightened Filters & Sizing"
                
            # 2. High-Performance Alpha Regime (Win rate >= 65% and Profit Factor >= 1.8)
            # Scale up profits: Expand profit target, increase position size, lower entry threshold slightly
            elif win_rate >= 65.0 and pf >= 1.8:
                tuned_params["MIN_ENTRY_SCORE"] = 78
                tuned_params["STOP_LOSS_PCT"] = 0.048
                tuned_params["TAKE_PROFIT_PCT"] = 0.120
                tuned_params["MAX_POSITION_PCT"] = 0.25
                tuned_params["RVOL_MIN"] = 1.3
                tuned_params["REASON"] = f"ALPHA EXPANSION: High WinRate ({win_rate:.1f}%) / PF ({pf:.2f}) -> Scaled Position Sizing & Trailing Profits"
                
            # 3. Steady Optimal Regime
            else:
                tuned_params["MIN_ENTRY_SCORE"] = 80
                tuned_params["STOP_LOSS_PCT"] = 0.045
                tuned_params["TAKE_PROFIT_PCT"] = 0.090
                tuned_params["MAX_POSITION_PCT"] = 0.20
                tuned_params["RVOL_MIN"] = 1.5
                tuned_params["REASON"] = f"BALANCED HARMONY: WinRate ({win_rate:.1f}%) / PF ({pf:.2f}) -> Optimal Institutional Balance"
                
        # Persist tuned parameters to JSON override file
        try:
            with open(self.config_override_file, "w", encoding="utf-8") as f:
                json.dump(tuned_params, f, indent=2, ensure_ascii=False)
            logger.info("✅ AutoTuning parameters saved: {} | Reason: {}", tuned_params, tuned_params["REASON"])
        except Exception as e:
            logger.error("Failed to save autotune config: {}", e)
            
        return tuned_params

if __name__ == "__main__":
    tuner = AutoTuningEngine()
    res = tuner.run_autotune()
    print("AutoTuning Result:", json.dumps(res, indent=2, ensure_ascii=False))
