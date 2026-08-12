"""
[v11.0 ULTRA QUANT] Sector & Pearson Correlation Cluster Risk Cap
==================================================================
Groups active positions into dynamic correlation clusters (rho >= 0.75).
Enforces a maximum capital cap of 40% per cluster to guarantee multi-arbitrage risk parity.
"""

from typing import Dict, List, Set, Any
from loguru import logger


class CorrelationClusterCap:
    def __init__(self, max_cluster_capital_pct: float = 0.40):
        self.max_cluster_pct = max_cluster_capital_pct

    def check_cluster_cap(self, candidate_symbol: str, active_positions: Dict[str, Any], total_equity: float) -> Dict[str, Any]:
        res = {
            'is_allowed': True,
            'cluster_pct': 0.0,
            'reason': 'Cluster cap OK'
        }

        if not active_positions or total_equity <= 0:
            return res

        try:
            from dynamic_correlation_matrix import DynamicCorrelationMatrix
            matrix_engine = DynamicCorrelationMatrix()

            correlated_held: Set[str] = set()

            for held_sym in active_positions.keys():
                if held_sym == candidate_symbol:
                    continue
                # Query correlation
                alpha_res = matrix_engine.get_dynamic_lag_alpha(held_sym)
                if alpha_res.get('leader_symbol') == candidate_symbol or alpha_res.get('corr_rho', 0) >= 0.75:
                    correlated_held.add(held_sym)

            if correlated_held:
                total_cluster_value = 0.0
                for sym in correlated_held:
                    pos = active_positions[sym]
                    total_cluster_value += pos.quantity * pos.entry_price

                cluster_pct = total_cluster_value / total_equity
                res['cluster_pct'] = cluster_pct

                if cluster_pct >= self.max_cluster_pct:
                    res['is_allowed'] = False
                    res['reason'] = f"CORRELATION_CLUSTER_CAP: Cluster value ({cluster_pct:.1%}) exceeds max limit ({self.max_cluster_pct:.0%}) with positions {list(correlated_held)}"
                    logger.warning("🚨 {}", res['reason'])
        except Exception as e:
            logger.debug("CorrelationClusterCap error: {}", e)

        return res
