"""
US Election & Political Policy Uncertainty Sentinel (us_election_policy_sentinel.py)
====================================================================================
Quantifies the impact of US Midterm/Presidential elections, legislative policy shifts,
and Economic Policy Uncertainty (EPU) on equity pricing and sector rotation.

Components:
1. FRED Daily US Economic Policy Uncertainty Index (USEPUINDXD)
2. US Midterm Election Seasonality & Historical 4-Year Cycle Engine (2026 Midterms)
3. Sector-Specific Political Sensitivity Baskets (Defense, Big Tech, Energy, Pharma)
4. Dynamic Policy Risk Score & Beta Throttler
"""

import os
import time
from datetime import datetime, date
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

_ELECTION_CACHE = {}
_ELECTION_TTL = 3600  # 1 Hour


@dataclass
class ElectionPolicySignal:
    epu_index: float                # Daily US Economic Policy Uncertainty
    epu_regime: str                 # "LOW", "MODERATE", "ELEVATED", "EXTREME"
    election_cycle_phase: str       # "MIDTERM_PRE_ELECTION_CHOP", "POST_ELECTION_RELIEF_RALLY", "OFF_YEAR_TREND"
    days_to_election: int           # Days until Nov 3, 2026 Midterm Election
    score_adjustment: int           # -20 to +10 pts
    favored_political_sectors: List[str]
    vulnerable_political_sectors: List[str]
    alerts: List[str]
    summary: str


class USElectionPolicySentinel:
    """Monitors US political cycles, legislative uncertainty, and midterm dynamics."""

    @staticmethod
    def get_next_election_info(today: date) -> Tuple[date, str, int]:
        """Dynamically computes the upcoming US General/Midterm Election Date via statutory calendar rules."""
        y = today.year if today.year % 2 == 0 else today.year + 1
        
        def _calc_election_tuesday(year: int) -> date:
            nov1 = date(year, 11, 1)
            first_mon_day = 1 + (7 - nov1.weekday()) % 7 if nov1.weekday() != 0 else 1
            return date(year, 11, first_mon_day + 1)
            
        elec_date = _calc_election_tuesday(y)
        if (today - elec_date).days > 60:
            y += 2
            elec_date = _calc_election_tuesday(y)
            
        elec_type = "PRESIDENTIAL" if y % 4 == 0 else "MIDTERM"
        days_to = (elec_date - today).days
        return elec_date, elec_type, days_to

    def __init__(self):
        from fred_macro import FREDMacroAnalyzer
        self.fred = FREDMacroAnalyzer()

    def evaluate(self) -> ElectionPolicySignal:
        now = time.time()
        if 'signal' in _ELECTION_CACHE:
            ts, sig = _ELECTION_CACHE['signal']
            if now - ts < _ELECTION_TTL:
                return sig

        try:
            import pytz
            today = datetime.now(pytz.timezone('America/New_York')).date()
        except Exception:
            today = datetime.utcnow().date()

        alerts = []
        score_adj = 0

        # 1. Fetch FRED Economic Policy Uncertainty Index (USEPUINDXD)
        epu_val = 180.0
        try:
            df_epu = self.fred.fetch_series_df("USEPUINDXD", limit=15)
            if not df_epu.empty:
                epu_val = float(df_epu['Close'].iloc[-1])
        except Exception as e:
            logger.debug("EPU fetch fallback: {}", e)

        if epu_val > 280:
            epu_regime = "EXTREME"
            score_adj -= 15
            alerts.append(f"🏛️ [POLICY_UNCERTAINTY_SPIKE] EPU Index at {epu_val:.1f} (>280). Market multiples compressing on legislative fog.")
        elif epu_val > 200:
            epu_regime = "ELEVATED"
            score_adj -= 5
            alerts.append(f"🏛️ [POLICY_CAUTION] EPU Index at {epu_val:.1f} (Elevated pre-election debates).")
        elif epu_val < 130:
            epu_regime = "LOW"
            score_adj += 5
            alerts.append(f"🏛️ [POLICY_STABILITY] EPU Index at {epu_val:.1f} (Calm legislative backdrop).")
        else:
            epu_regime = "MODERATE"

        # 2. Dynamic Election Cycle Phase
        elec_date, elec_type, days_to_elec = self.get_next_election_info(today)

        if 0 < days_to_elec <= 90:
            # Pre-Election Volatility Window
            cycle_phase = f"{elec_type}_PRE_ELECTION_CHOP"
            alerts.append(f"🗳️ [{elec_type}_CYCLE] D-{days_to_elec} to US {elec_type.capitalize()} Election ({elec_date}). Historical pre-election chop active (Favor high-quality leaders).")
        elif -60 <= days_to_elec <= 0:
            # Post-Election Historical Relief Surge
            cycle_phase = "POST_ELECTION_RELIEF_RALLY"
            score_adj += 10
            alerts.append(f"🚀 [ELECTION_RELIEF_RALLY] Post-election legislative clarity unlocked! High-Beta momentum boost active.")
        else:
            cycle_phase = "OFF_YEAR_TREND"

        favored = ['ITA', 'XLI', 'XLE']
        vulnerable = ['XLV', 'XLY']

        summary = (
            f"EPU Index: {epu_val:.1f} ({epu_regime}) | "
            f"Cycle: {cycle_phase} (D-{days_to_elec} days to {elec_date}) | "
            f"Policy Adj: {score_adj:+d} pts"
        )

        sig = ElectionPolicySignal(
            epu_index=round(epu_val, 1),
            epu_regime=epu_regime,
            election_cycle_phase=cycle_phase,
            days_to_election=days_to_elec,
            score_adjustment=score_adj,
            favored_political_sectors=favored,
            vulnerable_political_sectors=vulnerable,
            alerts=alerts,
            summary=summary
        )

        _ELECTION_CACHE['signal'] = (now, sig)
        return sig

    def evaluate_symbol_political_fit(self, symbol: str) -> Dict[str, Any]:
        """Evaluates whether a specific stock has tailwinds or headwinds from political policy."""
        sig = self.evaluate()
        bonus = 0
        reason = "Neutral political backdrop"

        sym_upper = symbol.upper()
        # Check defense & national security stocks (e.g. VTOL, NOC, LMT)
        if sym_upper in self.POLITICAL_SECTORS['DEFENSE']['tickers']:
            bonus = +5
            reason = "Defense & National Security budget tailwind"
        elif sym_upper in self.POLITICAL_SECTORS['SEMIS_AI']['tickers']:
            # AI & Semis have strategic national interest support (CHIPS Act)
            bonus = +3
            reason = "Strategic Sovereign AI & Critical Tech support"

        return {
            "symbol": symbol,
            "bonus": bonus + (sig.score_adjustment // 2),  # Blend general policy score
            "reason": reason,
            "epu_regime": sig.epu_regime
        }


def get_election_policy_sentinel() -> USElectionPolicySentinel:
    return USElectionPolicySentinel()

def get_election_policy_signal() -> ElectionPolicySignal:
    return USElectionPolicySentinel().evaluate()
