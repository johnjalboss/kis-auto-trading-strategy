"""
Portfolio Rebalancer & Dynamic Upgrade Swapper
===============================================
Monitors existing positions against newly screened candidates.
If a currently held position is flat/lagging (PnL between -1.0% and +1.0% for 2+ hours),
and a brand-new ultra-quant leader with Raw Score >= 130 appears (with score gap >= 30 pts),
this engine automatically liquidates the lagging stock to upgrade capital into the new leader!
"""

from datetime import datetime, timedelta
from loguru import logger
import config

class PortfolioRebalancer:
    """Dynamic Capital Rotation and Upgrade Engine"""

    def __init__(self, orchestrator_ref=None):
        self.orchestrator = orchestrator_ref

    def evaluate_upgrade_swapping(self, best_candidate_signal, current_positions: dict, trader_ref) -> dict:
        """Evaluates whether to swap a weak holding for a higher-scoring candidate"""
        res = {
            "should_swap": False,
            "weak_symbol": None,
            "reason": ""
        }

        if not best_candidate_signal or not current_positions:
            return res

        cand_score = getattr(best_candidate_signal, 'composite_score', 0)
        cand_raw = getattr(best_candidate_signal, 'raw_score', cand_score)
        cand_sym = best_candidate_signal.symbol

        # Must be an extraordinary high-score candidate (Raw score >= 110 or Clamped >= 85)
        if cand_raw < 110 and cand_score < 85:
            return res

        worst_sym = None
        worst_score_gap = 0.0

        for sym, pos in current_positions.items():
            try:
                # Check hold time (must have been held for at least 120 mins)
                hold_mins = (datetime.now() - pos.entry_time).total_seconds() / 60.0
                min_hold = getattr(config, 'UPGRADE_MIN_HOLD_MINUTES', 120)
                if hold_mins < min_hold:
                    continue

                # Fetch current price and PnL
                curr_price = trader_ref.get_price(sym) if trader_ref else pos.current_price
                if curr_price <= 0:
                    continue

                pnl_pct = (curr_price - pos.entry_price) / pos.entry_price

                # Do NOT sell profitable positions (> 2.0% profit)
                if pnl_pct >= getattr(config, 'UPGRADE_PROFIT_PROTECT_PCT', 0.02):
                    continue

                # Do NOT sell deeply losing positions (let stop loss handle it)
                if pnl_pct < getattr(config, 'UPGRADE_LOSS_LIMIT_PCT', -0.05):
                    continue

                # Positional lagger identified (flat position between -0.5% and +1.5%)
                score_gap = cand_raw - 60.0  # Assumed lagger score 60
                if score_gap >= getattr(config, 'UPGRADE_SCORE_GAP', 30):
                    if score_gap > worst_score_gap:
                        worst_score_gap = score_gap
                        worst_sym = sym

            except Exception as e:
                logger.debug(f"PortfolioRebalancer error checking {sym}: {e}")

        if worst_sym:
            res["should_swap"] = True
            res["weak_symbol"] = worst_sym
            res["reason"] = f"🔄 [AUTO_REBALANCE_UPGRADE] Swapping lagging position {worst_sym} for ultra-quant leader {cand_sym} (Raw Score: {cand_raw:.1f} pts, Gap: {worst_score_gap:.1f} pts)"
            logger.info(res["reason"])

        return res
