"""
Options Gamma Exposure & Market-Maker Hedging Engine (options_gamma_engine.py)
=============================================================================
Calculates:
  1. Net Gamma Exposure (GEX in $ Millions)
  2. Call Wall (Major Overhead Ceiling / Take-Profit Magnet)
  3. Put Wall (Major Floor Support / Structural Stop Buffer)
  4. Gamma Flip Level (Regime boundary between High Volatility & Low Volatility)
  5. Gamma Regime (POSITIVE_GAMMA vs NEGATIVE_GAMMA)
"""

import os
import time
import math
import json
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from scipy.stats import norm
from loguru import logger

CACHE_DIR = "options_gamma_cache"

class OptionsGammaEngine:
    """Institutional Options Gamma Exposure (GEX) & Wall-Level Analyzer"""

    def __init__(self, cache_ttl_sec: int = 900):  # 15 min cache
        self.cache_ttl = cache_ttl_sec
        self.cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), CACHE_DIR)
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_path(self, symbol: str) -> str:
        return os.path.join(self.cache_dir, f"{symbol.upper()}_gex.json")

    def _load_cache(self, symbol: str) -> Optional[Dict[str, Any]]:
        cpath = self._get_cache_path(symbol)
        if os.path.exists(cpath):
            try:
                with open(cpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if time.time() - data.get("timestamp", 0) < self.cache_ttl:
                    # Dynamically ensure nearest_expiration and dte_days are fresh based on US Eastern Time
                    try:
                        import pytz
                        today_et = datetime.now(pytz.timezone('America/New_York')).date()
                    except Exception:
                        today_et = datetime.utcnow().date()

                    if not data.get("nearest_expiration"):
                        days_to_fri = (4 - today_et.weekday()) % 7
                        data["nearest_expiration"] = (today_et + timedelta(days=days_to_fri if days_to_fri > 0 else 7)).strftime("%Y-%m-%d")

                    try:
                        exp_obj = datetime.strptime(data["nearest_expiration"], "%Y-%m-%d").date()
                        data["dte_days"] = max(0, (exp_obj - today_et).days)
                    except Exception:
                        data["dte_days"] = 1

                    return data
            except Exception as e:
                logger.debug("Failed loading GEX cache for {}: {}", symbol, e)
        return None

    def _save_cache(self, symbol: str, data: Dict[str, Any]):
        cpath = self._get_cache_path(symbol)
        try:
            data["timestamp"] = time.time()
            data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(cpath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.debug("Failed saving GEX cache for {}: {}", symbol, e)

    @staticmethod
    def _bs_gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculates Black-Scholes Gamma"""
        if S <= 0 or K <= 0 or T <= 0.001 or sigma <= 0.01:
            return 0.0
        try:
            d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))
            return float(gamma)
        except Exception:
            return 0.0

    def analyze_gex(self, symbol: str = "SPY") -> Dict[str, Any]:
        """
        Fetches option chain via yfinance and computes GEX profile, Call Wall, Put Wall, and Gamma Flip.
        """
        symbol = symbol.upper()
        cached = self._load_cache(symbol)
        if cached:
            return cached

        try:
            import yfinance as yf
            ticker_cls = getattr(yf, '_original_yf_Ticker', yf.Ticker)
            ticker = ticker_cls(symbol)
            expirations = ticker.options
            
            # Fetch current stock price robustly
            current_price = 0.0
            try:
                fast = getattr(ticker, 'fast_info', {})
                current_price = float(fast.get("last_price", 0.0) or fast.get("regularMarketPrice", 0.0) or 0.0)
            except Exception:
                current_price = 0.0
                
            if current_price <= 0:
                try:
                    h = ticker.history(period="5d", interval="1d")
                    if not h.empty:
                        current_price = float(h['Close'].iloc[-1])
                except Exception:
                    current_price = 100.0

            if not expirations:
                # Synthetic model fallback for non-optionable / API fallback
                return self._generate_synthetic_gex(symbol, current_price)

            # Analyze nearest 8 standard monthly/weekly expirations for full institutional GEX
            target_exps = expirations[:8]
            all_calls = []
            all_puts = []

            r = 0.045  # Approx risk-free rate 4.5%
            today = datetime.today()

            for exp_str in target_exps:
                try:
                    chain = ticker.option_chain(exp_str)
                    exp_dt = datetime.strptime(exp_str, "%Y-%m-%d")
                    T = max(0.005, (exp_dt - today).days / 365.0)

                    if chain.calls is not None and not chain.calls.empty:
                        c_df = chain.calls.copy()
                        c_df['T'] = T
                        c_df['exp_str'] = exp_str
                        all_calls.append(c_df)

                    if chain.puts is not None and not chain.puts.empty:
                        p_df = chain.puts.copy()
                        p_df['T'] = T
                        p_df['exp_str'] = exp_str
                        all_puts.append(p_df)
                except Exception as e:
                    logger.debug("Option chain fetch error for {} exp {}: {}", symbol, exp_str, e)

            if not all_calls and not all_puts:
                return self._generate_synthetic_gex(symbol, current_price)

            df_calls = pd.concat(all_calls, ignore_index=True) if all_calls else pd.DataFrame()
            df_puts = pd.concat(all_puts, ignore_index=True) if all_puts else pd.DataFrame()

            # Clean and calculate effective open interest (OI or Volume-weighted proxy)
            for df in [df_calls, df_puts]:
                if not df.empty:
                    df['oi'] = df['openInterest'].fillna(0).astype(float) if 'openInterest' in df.columns else 0.0
                    df['vol'] = df['volume'].fillna(0).astype(float) if 'volume' in df.columns else 0.0
                    df['eff_contracts'] = np.maximum(df['oi'], df['vol'] * 0.40)
                    df['impliedVolatility'] = df['impliedVolatility'].fillna(0.20).clip(lower=0.05, upper=2.0)

            # Calculate Dollar Gamma ($GEX in Millions)
            call_gex_by_strike = {}
            put_gex_by_strike = {}

            # Filter strikes near current price (+/- 20%) for accurate institutional walls
            lower_k = current_price * 0.80
            upper_k = current_price * 1.20

            if not df_calls.empty:
                for _, row in df_calls.iterrows():
                    k = float(row['strike'])
                    if not (lower_k <= k <= upper_k):
                        continue
                    contracts = float(row['eff_contracts'])
                    if contracts <= 0:
                        continue
                    sigma = float(row['impliedVolatility'])
                    t = float(row['T'])
                    g = self._bs_gamma(current_price, k, t, r, sigma)
                    dollar_g = (g * current_price * contracts * 100 * current_price * 0.01) / 1e6
                    call_gex_by_strike[k] = call_gex_by_strike.get(k, 0.0) + dollar_g

            if not df_puts.empty:
                for _, row in df_puts.iterrows():
                    k = float(row['strike'])
                    if not (lower_k <= k <= upper_k):
                        continue
                    contracts = float(row['eff_contracts'])
                    if contracts <= 0:
                        continue
                    sigma = float(row['impliedVolatility'])
                    t = float(row['T'])
                    g = self._bs_gamma(current_price, k, t, r, sigma)
                    dollar_g = (g * current_price * contracts * 100 * current_price * 0.01) / 1e6
                    put_gex_by_strike[k] = put_gex_by_strike.get(k, 0.0) + dollar_g

            # Compute Call Wall (Highest Call GEX strictly above spot) and Put Wall (Highest Put GEX strictly below spot)
            calls_above = {k: v for k, v in call_gex_by_strike.items() if k >= current_price * 1.002}
            puts_below = {k: v for k, v in put_gex_by_strike.items() if k <= current_price * 0.998}

            call_wall = max(calls_above, key=calls_above.get) if calls_above else round(current_price * 1.045, 2)
            put_wall = max(puts_below, key=puts_below.get) if puts_below else round(current_price * 0.955, 2)

            total_call_gex = sum(call_gex_by_strike.values())
            total_put_gex = sum(put_gex_by_strike.values())
            net_gex = total_call_gex - total_put_gex  # in $ Millions

            # Gamma Flip Level (Approximation where cumulative net gamma crosses zero)
            all_strikes = sorted(set(list(call_gex_by_strike.keys()) + list(put_gex_by_strike.keys())))
            cum_gex = 0.0
            gamma_flip = round(current_price, 2)
            for k in all_strikes:
                cum_gex += call_gex_by_strike.get(k, 0.0) - put_gex_by_strike.get(k, 0.0)
                if cum_gex >= 0:
                    gamma_flip = round(k, 2)
                    break

            is_pos_gamma = net_gex >= 0.0
            gex_regime = "POSITIVE_GAMMA" if is_pos_gamma else "NEGATIVE_GAMMA"
            vol_profile = "LOW_VOLATILITY_UPTREND" if is_pos_gamma else "HIGH_VOLATILITY_EXPANSION"

            # Calculate dynamic DTE based on US Eastern Time
            try:
                import pytz
                today_et = datetime.now(pytz.timezone('America/New_York')).date()
            except Exception:
                today_et = datetime.utcnow().date()

            days_to_fri = (4 - today_et.weekday()) % 7
            default_fri = (today_et + timedelta(days=days_to_fri if days_to_fri > 0 else 7)).strftime("%Y-%m-%d")
            
            # Select target expiration with significant volume (prefer next weekly or monthly)
            nearest_exp = target_exps[0] if target_exps else default_fri
            for exp_c in target_exps:
                exp_c_obj = datetime.strptime(exp_c, "%Y-%m-%d").date()
                if (exp_c_obj - today_et).days >= 2:
                    nearest_exp = exp_c
                    break

            try:
                exp_date_obj = datetime.strptime(nearest_exp, "%Y-%m-%d").date()
                dte_calc = max(0, (exp_date_obj - today_et).days)
            except Exception:
                dte_calc = max(0, days_to_fri)

            total_contracts = float(df_calls['eff_contracts'].sum() + df_puts['eff_contracts'].sum()) if not df_calls.empty or not df_puts.empty else 0.0
            is_thin = total_contracts < 200.0

            result = {
                "symbol": symbol,
                "current_price": round(current_price, 2),
                "net_gex_millions": round(net_gex, 2),
                "total_open_interest": int(total_oi),
                "is_thin_options": is_thin,
                "call_wall": round(call_wall, 2),
                "put_wall": round(put_wall, 2),
                "gamma_flip_level": round(gamma_flip, 2),
                "call_wall_dist_pct": round((call_wall - current_price) / current_price * 100, 2),
                "put_wall_dist_pct": round((put_wall - current_price) / current_price * 100, 2),
                "nearest_expiration": nearest_exp,
                "dte_days": dte_calc,
                "gex_regime": gex_regime,
                "volatility_profile": vol_profile,
                "is_synthetic": False
            }

            self._save_cache(symbol, result)
            return result

        except Exception as e:
            logger.debug("Options GEX analysis fallback for {}: {}", symbol, e)
            return self._generate_synthetic_gex(symbol, current_price if 'current_price' in locals() and current_price > 0 else 100.0)

    def _generate_synthetic_gex(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """Calculates quantitative statistical volatility bands (1.5-sigma) when option chain is unlisted/unavailable."""
        try:
            import pytz
            today_et = datetime.now(pytz.timezone('America/New_York')).date()
        except Exception:
            today_et = datetime.utcnow().date()

        days_to_fri = (4 - today_et.weekday()) % 7
        nearest_fri_obj = today_et + timedelta(days=days_to_fri if days_to_fri > 0 else 7)
        nearest_exp = nearest_fri_obj.strftime("%Y-%m-%d")
        dte_calc = max(1, (nearest_fri_obj - today_et).days)

        # 1. Compute actual historical volatility from 20-day price series
        sigma_ann = 0.25  # default 25% annualized volatility
        try:
            import yfinance as yf
            import numpy as np
            t = yf.Ticker(symbol)
            hist = t.history(period="1mo", interval="1d")
            if not hist.empty and len(hist) >= 5:
                if current_price <= 0:
                    current_price = float(hist['Close'].iloc[-1])
                returns = np.diff(np.log(hist['Close'].values))
                if len(returns) > 0 and np.std(returns) > 0:
                    sigma_ann = float(np.std(returns) * np.sqrt(252))
        except Exception:
            pass

        if current_price <= 0:
            current_price = 100.0

        # 2. Derive 1.5-sigma statistical price boundary for remaining DTE
        sigma_dte = sigma_ann * math.sqrt(dte_calc / 252.0)
        call_wall = round(current_price * (1.0 + 1.5 * sigma_dte), 2)
        put_wall = round(current_price * (1.0 - 1.5 * sigma_dte), 2)
        gamma_flip = round(current_price * (1.0 - 0.5 * sigma_dte), 2)

        result = {
            "symbol": symbol,
            "current_price": round(current_price, 2),
            "net_gex_millions": 0.0,  # 0.0 unlisted/no dealer inventory
            "call_wall": call_wall,
            "put_wall": put_wall,
            "gamma_flip_level": gamma_flip,
            "call_wall_dist_pct": round((call_wall - current_price) / current_price * 100, 2),
            "put_wall_dist_pct": round((put_wall - current_price) / current_price * 100, 2),
            "nearest_expiration": nearest_exp,
            "dte_days": dte_calc,
            "gex_regime": "STATISTICAL_VOLATILITY_BAND (HV 통계 밴드)",
            "volatility_profile": f"HV {sigma_ann*100:.1f}% 1.5σ 표준편차 밴드",
            "is_synthetic": True
        }

        self._save_cache(symbol, result)
        return result

    def format_telegram_card(self, symbol: str = "SPY") -> str:
        """Formats the Options Gamma status for Telegram"""
        data = self.analyze_gex(symbol)
        regime_emoji = "🟢" if data["gex_regime"] == "POSITIVE_GAMMA" else "🔴"
        regime_desc = "변동성 안정 / 매수 핀(Pin)" if data["gex_regime"] == "POSITIVE_GAMMA" else "변동성 확대 / 추세 가속"
        
        c_dist = data['call_wall_dist_pct']
        p_dist = data['put_wall_dist_pct']
        c_sign = "+" if c_dist >= 0 else ""
        p_sign = "+" if p_dist >= 0 else ""

        card = (
            f"🧮 <b>[옵션 감마 익스포저(GEX) & 마켓메이커 헤징 리포트]</b>\n"
            f"<i>지수/종목: <b>{data['symbol']}</b> (현재가: ${data['current_price']:.2f})</i>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⚡️ <b>순 감마(Net GEX)</b>: <code>${data['net_gex_millions']:+,.1f}M USD</code>\n"
            f"📡 <b>감마 레짐</b>: {regime_emoji} <b>{data['gex_regime']}</b> ({regime_desc})\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🧱 <b>주요 매물대 & 마켓메이커 헤징 벽 (Walls)</b>:\n"
            f"  • 🎯 <b>Call Wall (상단 저항 벽)</b>: <code>${data['call_wall']:.2f}</code> ({c_sign}{c_dist:.2f}%)\n"
            f"  • 🛡️ <b>Put Wall (하단 지지 바닥)</b>: <code>${data['put_wall']:.2f}</code> ({p_sign}{p_dist:.2f}%)\n"
            f"  • ⚖️ <b>Gamma Flip (변동성 분기점)</b>: <code>${data['gamma_flip_level']:.2f}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💡 <i>Call Wall 상단은 딜러의 매도 헤징으로 강력한 저항이 되며, Put Wall 하단은 강력한 지지선으로 작용합니다.</i>"
        )
        return card

# Singleton helper
_options_gamma_instance = None

def get_options_gamma_engine() -> OptionsGammaEngine:
    global _options_gamma_instance
    if _options_gamma_instance is None:
        _options_gamma_instance = OptionsGammaEngine()
    return _options_gamma_instance

get_gamma_engine = get_options_gamma_engine


if __name__ == "__main__":
    engine = get_options_gamma_engine()
    print(json.dumps(engine.analyze_gex("SPY"), indent=2, ensure_ascii=False))
    print("\nTelegram Card:\n", engine.format_telegram_card("SPY"))
