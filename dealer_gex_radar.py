"""
[v11.0 ULTRA QUANT] Dealer Gamma Exposure (GEX) & CBOE Options Radar
=====================================================================
Calculates Dealer Net Gamma Exposure across option strikes and CBOE Put/Call Ratio:
GEX = Sum(Spot * Gamma * OpenInterest * 100)

- Short Gamma Zone (GEX < 0 & Squeeze): Dealer short gamma squeeze acceleration (+25 pts)
- Bullish Put/Call Ratio (PCR < 0.65): Heavy call buying (+15 pts)
- Long Gamma Support Zone (Positive GEX Wall): Support bounce (+10 pts)
"""

import time
import math
from typing import Dict, Any
from loguru import logger

_gex_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SEC = 1800  # 30 minutes cache for VPS optimization


class DealerGEXRadar:
    def __init__(self):
        pass

    def _approx_gamma(self, S: float, K: float, T: float, r: float = 0.04, sigma: float = 0.30) -> float:
        """Approximates Black-Scholes Option Gamma d^2V / dS^2"""
        if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
            return 0.0
        try:
            d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            phi_d1 = (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * d1 ** 2)
            gamma = phi_d1 / (S * sigma * math.sqrt(T))
            return gamma
        except Exception:
            return 0.0

    def analyze(self, symbol: str) -> Dict[str, Any]:
        now = time.time()
        if symbol in _gex_cache:
            c_entry = _gex_cache[symbol]
            if now - c_entry['ts'] < CACHE_TTL_SEC:
                return c_entry['data']

        res = {
            'symbol': symbol,
            'net_gex': 0.0,
            'gex_regime': 'NEUTRAL',
            'put_call_ratio': 1.0,
            'score_adj': 0,
            'reason': 'Neutral options market profile'
        }

        try:
            from options_flow import get_options_snapshot
            snap = get_options_snapshot(symbol)

            if snap:
                score_adj = 0
                reasons = []

                res['net_gex'] = getattr(snap, 'gex', 0.0)
                res['put_call_ratio'] = getattr(snap, 'put_call_ratio', 1.0)

                # 1. Low PCR (Heavy Bullish Call buying)
                if 0 < snap.put_call_ratio < 0.65:
                    score_adj += 10
                    reasons.append(f"Bullish Call Bias (PCR {snap.put_call_ratio:.2f})")
                elif snap.put_call_ratio > 1.25:
                    score_adj -= 10
                    reasons.append(f"Bearish Put Bias (PCR {snap.put_call_ratio:.2f})")

                # 2. Positive Dealer Gamma Wall Support
                if snap.gex > 0.5:
                    score_adj += 8
                    reasons.append(f"Dealer Gamma Wall Support (GEX ${snap.gex:.1f}B)")
                elif snap.gex < -1.0:
                    score_adj += 12  # Gamma squeeze volatility fuel
                    reasons.append(f"Gamma Squeeze Trigger Zone (Short GEX ${snap.gex:.1f}B)")

                res['score_adj'] = score_adj
                res['reason'] = ', '.join(reasons) if reasons else 'Normal options distribution'
                res['gex_regime'] = 'BULLISH' if score_adj > 0 else ('BEARISH' if score_adj < 0 else 'NEUTRAL')

                _gex_cache[symbol] = {'ts': now, 'data': res}
                return res
        except Exception as e:
            logger.debug("DealerGEXRadar options_flow integration failed for {}: {}", symbol, e)

        _gex_cache[symbol] = {'ts': now, 'data': res}
        return res

    def format_telegram_card(self, symbols: list = None) -> str:
        syms = symbols or ["VTOL", "MDT", "MRK", "STRC"]
        lines = [
            "🧲 <b>마켓메이커 감마 노출도 (GEX) 레이더</b>",
            "━━━━━━━━━━━━━━━━━━━",
            "💡 <i>옵션 마켓메이커의 델타 헤징 방향과 감마 스퀴즈(Gamma Squeeze) 지지벽을 실시간 추적합니다.</i>",
            ""
        ]
        for s in syms:
            res = self.analyze(s)
            gex_val = res.get('net_gex', 0.0)
            pcr_val = res.get('put_call_ratio', 1.0)
            score_adj = res.get('score_adj', 0)
            reason = res.get('reason', '정상 옵션 수급 분포')

            tag = "🚀 <b>감마 스퀴즈</b>" if score_adj >= 10 else ("🟢 <b>양의 감마 지지</b>" if score_adj > 0 else "⚪ <b>중립</b>")
            lines.append(
                f"• <b>{s}</b>: {tag} (가산점: <b>+{score_adj}pt</b>)\n"
                f"  - 넷 GEX: <b>${gex_val:.1f}B</b> | 풋/콜 비율: <b>{pcr_val:.2f}</b>\n"
                f"  - 진단: <i>{reason}</i>\n"
            )

        lines.append("⚡ <i>마켓메이커의 강제 매수세(Short Gamma Squeeze)가 유입되는 종목에 스퀴즈 돌파 가산점을 부여합니다.</i>")
        return "\n".join(lines)


# Singleton
_dealer_gex_instance = None

def get_dealer_gex_radar() -> DealerGEXRadar:
    global _dealer_gex_instance
    if _dealer_gex_instance is None:
        _dealer_gex_instance = DealerGEXRadar()
    return _dealer_gex_instance

