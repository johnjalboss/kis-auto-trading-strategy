"""
[v11.0 ULTRA QUANT] Dealer Gamma Exposure (GEX) Radar
====================================================
Calculates Dealer Net Gamma Exposure across option strikes:
GEX = Sum(Spot * Gamma * OpenInterest * 100)

Short Gamma Zone (GEX < 0): Dealer short gamma squeeze acceleration (+25 pts)
Long Gamma Zone (GEX > 0): Dealer long gamma pinning/damping (-15 pts)
"""

import time
import math
from typing import Dict, Any
from loguru import logger

_gex_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SEC = 1800  # 30 minutes cache for 1GB VPS RAM optimization


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
            'score_adj': 0,
            'reason': 'No options GEX data'
        }

        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            expirations = ticker.options
            if not expirations:
                _gex_cache[symbol] = {'ts': now, 'data': res}
                return res

            spot_price = float(ticker.fast_info.last_price or 0.0)
            if spot_price <= 0:
                _gex_cache[symbol] = {'ts': now, 'data': res}
                return res

            # Analyze nearest expiration date
            exp_date = expirations[0]
            opt = ticker.option_chain(exp_date)
            calls = opt.calls
            puts = opt.puts

            # Calculate expiration T in years
            from datetime import datetime
            exp_dt = datetime.strptime(exp_date, '%Y-%m-%d')
            days_to_exp = max(1, (exp_dt - datetime.now()).days)
            T = days_to_exp / 365.0

            total_call_gex = 0.0
            total_put_gex = 0.0

            if calls is not None and not calls.empty:
                for _, row in calls.iterrows():
                    strike = float(row.get('strike', 0))
                    oi = float(row.get('openInterest', 0) or 0)
                    iv = float(row.get('impliedVolatility', 0) or 0.30)
                    if strike > 0 and oi > 0:
                        gamma = self._approx_gamma(spot_price, strike, T, sigma=max(0.05, iv))
                        total_call_gex += spot_price * gamma * oi * 100.0

            if puts is not None and not puts.empty:
                for _, row in puts.iterrows():
                    strike = float(row.get('strike', 0))
                    oi = float(row.get('openInterest', 0) or 0)
                    iv = float(row.get('impliedVolatility', 0) or 0.30)
                    if strike > 0 and oi > 0:
                        gamma = self._approx_gamma(spot_price, strike, T, sigma=max(0.05, iv))
                        # Dealer is long call gamma, short put gamma
                        total_put_gex += spot_price * gamma * oi * 100.0

            net_gex = (total_call_gex - total_put_gex) / 1e6  # In $M

            if net_gex < -1.0:
                res['gex_regime'] = 'SHORT_GAMMA_SQUEEZE'
                res['score_adj'] = 25
                res['reason'] = f"Dealer Short Gamma Squeeze Zone (Net GEX: ${net_gex:.1f}M)"
            elif net_gex > 5.0:
                res['gex_regime'] = 'LONG_GAMMA_PINNED'
                res['score_adj'] = -10
                res['reason'] = f"Dealer Long Gamma Pinning Zone (Net GEX: ${net_gex:.1f}M)"
            else:
                res['gex_regime'] = 'NEUTRAL'
                res['score_adj'] = 0
                res['reason'] = f"Neutral GEX (${net_gex:.1f}M)"

            res['net_gex'] = net_gex
        except Exception as e:
            logger.debug("DealerGEXRadar analysis failed for {}: {}", symbol, e)

        _gex_cache[symbol] = {'ts': now, 'data': res}
        return res
