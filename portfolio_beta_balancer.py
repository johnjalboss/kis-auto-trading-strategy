"""
Portfolio Beta Balancer & Inverse ETF Engine (portfolio_beta_balancer.py)
========================================================================
Designed by World #1 Quant Systems Architecture.

Key Principles:
1. BULL MARKET (BULL_NORMAL / BULL_TRENDING / VIX < 18):
   - Beta throttle is UNLOCKED (Max Beta 2.5x).
   - Allows 100% aggressive capture of high-beta tech/growth leaders (NVDA, AAPL, MSFT, AMD, PLTR).
2. CHOPPY / SECTOR ROTATION MARKET (CHOPPY / TRANSITION):
   - Beta balanced to 1.1x ~ 1.3x with quality healthcare/defensives (MRK, MDT).
3. SYSTEMIC CRASH / PANIC (BEAR_PANIC / CRASH / VIX > 28):
   - Defensives also fall during broad liquidity crashes.
   - Activates Inverse ETF Mode (SQQQ, SH, SOXS) or 100% Cash Preservation for crash profit!
"""

from typing import Dict, Any, List
from loguru import logger
import config

# Benchmark Beta Reference Table
BETA_MAP = {
    # Tech / High Growth (Beta 1.4 ~ 2.2)
    "NVDA": 2.15, "AMD": 1.95, "TSLA": 2.30, "TQQQ": 3.00, "SOXL": 3.20,
    "AAPL": 1.15, "MSFT": 1.20, "GOOGL": 1.25, "AMZN": 1.30, "META": 1.40,
    "PLTR": 2.20, "ARM": 2.40, "MU": 1.70, "AVGO": 1.55, "VTOL": 1.25, "STRC": 1.10,
    # Healthcare / Defensives (Beta 0.4 ~ 0.8)
    "MRK": 0.45, "MDT": 0.72, "JNJ": 0.55, "PFE": 0.65, "PG": 0.48, "KO": 0.52, "PEP": 0.58,
    # Inverse ETFs (Crash Protectors)
    "SQQQ": -3.00, "SOXS": -3.20, "SH": -1.00, "PSQ": -1.00
}

class PortfolioBetaBalancer:
    """Regime-Adaptive Portfolio Beta Balancer & Crash Engine"""

    def __init__(self):
        pass

    def calculate_portfolio_beta(self, positions: Dict[str, Any]) -> float:
        """Calculates value-weighted portfolio beta."""
        if not positions:
            return 1.0
        total_val = 0.0
        weighted_beta_sum = 0.0
        for sym, pos in positions.items():
            qty = getattr(pos, 'quantity', 1)
            p = getattr(pos, 'current_price', getattr(pos, 'entry_price', 100.0))
            val = qty * p
            beta = BETA_MAP.get(sym, 1.10)
            weighted_beta_sum += val * beta
            total_val += val

        return round(weighted_beta_sum / total_val, 2) if total_val > 0 else 1.0

    def evaluate_new_symbol_beta_fit(self, symbol: str, current_positions: Dict[str, Any], regime: str = "BULL_NORMAL") -> Dict[str, Any]:
        """
        Evaluates whether adding symbol maintains optimal portfolio beta for current regime.
        """
        sym_beta = BETA_MAP.get(symbol, 1.10)
        port_beta = self.calculate_portfolio_beta(current_positions)
        
        is_bull = "BULL" in regime
        is_panic = regime in {"BEAR_PANIC", "CRASH", "SYSTEMIC_RISK"}
        is_inverse = symbol in getattr(config, 'INVERSE_ETFS', {"SQQQ", "SH", "PSQ", "SOXS"})

        # 1. Systemic Crash Mode: Inverse ETFs are highly encouraged
        if is_panic:
            if is_inverse:
                return {
                    "allowed": True,
                    "score_bonus": 25,
                    "reason": f"CRASH_ALPHA: Inverse ETF {symbol} prioritized for systemic crash profit!"
                }
            else:
                return {
                    "allowed": False,
                    "score_bonus": -30,
                    "reason": f"CRASH_DEFENSE: Long position {symbol} blocked during systemic panic."
                }

        # 2. Bull Market Mode: 100% Unlocked horsepower for growth leaders
        if is_bull:
            if is_inverse:
                return {"allowed": False, "score_bonus": -50, "reason": f"Inverse ETF {symbol} blocked in Bull Market."}
            return {
                "allowed": True,
                "score_bonus": 10 if sym_beta >= 1.3 else 5,
                "reason": f"BULL_ACCELERATION: High-Beta {symbol} (Beta={sym_beta}) unlocked for maximum upside."
            }

        # 3. Choppy / Transition Mode: Balanced risk
        if port_beta > 1.4 and sym_beta > 1.8:
            return {
                "allowed": True,
                "score_bonus": -10,
                "reason": f"BETA_DAMPING: Portfolio beta ({port_beta:.2f}) elevated in {regime}."
            }

        return {"allowed": True, "score_bonus": 0, "reason": f"Healthy Beta Fit ({sym_beta:.2f})"}

def get_portfolio_beta_balancer() -> PortfolioBetaBalancer:
    return PortfolioBetaBalancer()
