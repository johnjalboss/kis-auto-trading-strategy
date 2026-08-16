"""
Global Macro & Intermarket Flow Sentinel (global_macro.py)
==========================================================
Institutional Global Cross-Border Capital Flow & Risk Sentiment Engine.

Tracks:
1. 🇯🇵 Japan & Yen Carry Unwind Risk (FXY / USDJPY)
2. 🇨🇳 China & Emerging Markets Liquidity (FXI, EEM)
3. 🇪🇺 Europe Market Health (VGK, EZU)
4. 💵 US vs Global Capital Flow Relative Strength (SPY vs ACWI / EEM)
5. 🛢️ Commodities & Inflation Shocks (USO Oil, GLD Gold)
6. ₿ Crypto Risk Appetite (BTC-USD)
"""

import time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger

_GLOBAL_MACRO_CACHE = {}
_GLOBAL_MACRO_TTL = 1800  # 30 mins TTL


@dataclass
class GlobalMacroSignal:
    overall_risk: str  # "RISK_ON", "RISK_OFF", "CAUTION", "NEUTRAL"
    risk_score: int    # 0-100 (higher = more risk-off)
    usd_strength: str
    oil_signal: str
    crypto_signal: str
    yen_carry_risk: str
    china_signal: str
    europe_signal: str
    us_outperformance_ratio: float  # SPY vs EEM ratio slope (>0 = Capital rushing to US)
    active_alerts: List[str]
    stock_bias: str
    position_size_mult: float
    sectors_to_avoid: List[str]
    sectors_to_favor: List[str]
    recommendation: str

    @property
    def score(self) -> int:
        if self.overall_risk == "RISK_OFF":
            return -80
        elif self.overall_risk == "CAUTION":
            return -40
        elif self.overall_risk == "RISK_ON":
            return 40
        else:
            return 0


class GlobalMacroAnalyzer:
    SYMBOLS = {
        'SPY': 'SPY',        # US S&P 500
        'QQQ': 'QQQ',        # US Nasdaq
        'DXY': 'UUP',        # US Dollar Index ETF
        'USDJPY': 'FXY',     # Yen ETF (Strength = Carry unwind risk)
        'OIL': 'USO',        # Crude Oil
        'GOLD': 'GLD',       # Safe Haven Gold
        'BTC': 'BTC-USD',    # High-beta risk appetite
        'CHINA': 'FXI',      # China Large-Cap
        'EUROPE': 'VGK',     # Europe FTSE
        'EMERGING': 'EEM',   # Emerging Markets
    }

    def __init__(self):
        self.data_cache = {}

    def analyze(self) -> GlobalMacroSignal:
        now = time.time()
        if 'cached_signal' in _GLOBAL_MACRO_CACHE:
            ts, cached = _GLOBAL_MACRO_CACHE['cached_signal']
            if now - ts < _GLOBAL_MACRO_TTL:
                return cached

        self._fetch_data()
        alerts = []
        risk_score = 40  # Default mild risk-on baseline

        # 1. USD Strength
        usd = self._analyze_usd()
        if usd['signal'] == "STRONG":
            risk_score += 15
            alerts.append("💵 Strong USD - Headwind for US Multinationals")

        # 2. Oil / Inflation
        oil = self._analyze_oil()
        if oil['signal'] == "SPIKING":
            risk_score += 15
            alerts.append("🛢️ Oil Spiking - Inflation & Cost Pressure")

        # 3. Crypto High-Beta Risk Appetite
        crypto = self._analyze_crypto()
        if crypto['signal'] == "CRASHING":
            risk_score += 20
            alerts.append("₿ Crypto Liquidation - Broad Market Risk-Off")
        elif crypto['signal'] == "RALLYING":
            risk_score -= 10

        # 4. Japanese Yen Carry Unwind Risk
        yen = self._analyze_yen_carry()
        if yen['signal'] == "UNWINDING":
            risk_score += 30
            alerts.append("🇯🇵 YEN CARRY UNWINDING - Global Margin Liquidation Risk!")

        # 5. China & Emerging Market Rotation
        china = self._analyze_china()
        emerging = self._analyze_emerging()
        if china['signal'] == "CRASHING":
            risk_score += 10
            alerts.append("🇨🇳 China Market Stress - Global Supply Chain Risk")

        # 6. Europe Health
        europe = self._analyze_europe()
        if europe['signal'] == "CRASHING":
            risk_score += 10
            alerts.append("🇪🇺 Europe Market Downturn")

        # 7. US vs World Capital Flow (SPY / EEM Ratio)
        us_rel = self._get_us_relative_flow()
        if us_rel > 1.02:
            risk_score -= 10  # Capital fleeing foreign markets into US safety
            alerts.append("🇺🇸 Global Capital Inflow to US Equities (US Outperforming World)")
        elif us_rel < 0.98:
            alerts.append("🌏 Global Capital Rotating into Emerging/Foreign Markets")

        # Determine overall state
        if risk_score >= 75:
            overall = "RISK_OFF"
            bias = "BEARISH"
            size_mult = 0.4
            rec = "🚨 GLOBAL RISK-OFF: High macro cross-winds. Reduce exposure."
        elif risk_score >= 55:
            overall = "CAUTION"
            bias = "NEUTRAL"
            size_mult = 0.7
            rec = "⚠️ GLOBAL CAUTION: Selective entries only."
        elif risk_score <= 35:
            overall = "RISK_ON"
            bias = "BULLISH"
            size_mult = 1.0
            rec = "✅ GLOBAL RISK-ON: Favorable global liquidity flow for US Equities."
        else:
            overall = "NEUTRAL"
            bias = "NEUTRAL"
            size_mult = 0.9
            rec = "Balanced global capital flow environment."

        avoid = []
        favor = []
        if oil['signal'] == "SPIKING":
            avoid.extend(['XLY', 'JETS'])
            favor.append('XLE')
        if usd['signal'] == "STRONG":
            avoid.extend(['EEM', 'XLB'])
            favor.append('XLU')
        if yen['signal'] == "UNWINDING":
            avoid.extend(['XLF', 'XLK'])
            favor.extend(['XLU', 'GLD'])

        sig = GlobalMacroSignal(
            overall_risk=overall,
            risk_score=risk_score,
            usd_strength=usd['signal'],
            oil_signal=oil['signal'],
            crypto_signal=crypto['signal'],
            yen_carry_risk=yen['signal'],
            china_signal=china['signal'],
            europe_signal=europe['signal'],
            us_outperformance_ratio=round(us_rel, 3),
            active_alerts=alerts,
            stock_bias=bias,
            position_size_mult=size_mult,
            sectors_to_avoid=avoid,
            sectors_to_favor=favor,
            recommendation=rec
        )
        _GLOBAL_MACRO_CACHE['cached_signal'] = (now, sig)
        return sig

    def _fetch_data(self):
        for name, symbol in self.SYMBOLS.items():
            try:
                df = yf.download(symbol, period='1mo', progress=False)
                if df is not None and not df.empty:
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    self.data_cache[name] = df
            except Exception as err:
                logger.debug("Global data fetch skipped for {}: {}", symbol, err)

    def _get_change(self, name: str, days: int = 5) -> float:
        df = self.data_cache.get(name)
        if df is None or len(df) < days:
            return 0.0
        try:
            return (float(df['Close'].iloc[-1]) / float(df['Close'].iloc[-days]) - 1) * 100.0
        except Exception:
            return 0.0

    def _get_us_relative_flow(self) -> float:
        spy_df = self.data_cache.get('SPY')
        eem_df = self.data_cache.get('EMERGING')
        if spy_df is not None and eem_df is not None and len(spy_df) >= 5 and len(eem_df) >= 5:
            try:
                spy_ret = float(spy_df['Close'].iloc[-1]) / float(spy_df['Close'].iloc[-5])
                eem_ret = float(eem_df['Close'].iloc[-1]) / float(eem_df['Close'].iloc[-5])
                return spy_ret / eem_ret if eem_ret > 0 else 1.0
            except Exception:
                pass
        return 1.0

    def _analyze_usd(self) -> Dict[str, Any]:
        chg = self._get_change('DXY')
        if chg > 2.0:
            return {'signal': 'STRONG', 'change': chg}
        elif chg < -2.0:
            return {'signal': 'WEAK', 'change': chg}
        return {'signal': 'NEUTRAL', 'change': chg}

    def _analyze_oil(self) -> Dict[str, Any]:
        chg = self._get_change('OIL')
        if chg > 8.0:
            return {'signal': 'SPIKING', 'change': chg}
        elif chg < -8.0:
            return {'signal': 'CRASHING', 'change': chg}
        return {'signal': 'STABLE', 'change': chg}

    def _analyze_crypto(self) -> Dict[str, Any]:
        chg = self._get_change('BTC')
        if chg > 10.0:
            return {'signal': 'RALLYING', 'change': chg}
        elif chg < -10.0:
            return {'signal': 'CRASHING', 'change': chg}
        return {'signal': 'NEUTRAL', 'change': chg}

    def _analyze_yen_carry(self) -> Dict[str, Any]:
        # FXY up > 2.5% in 5 days means Yen strengthening rapidly -> Carry trade unwinding
        chg = self._get_change('USDJPY')
        if chg > 2.5:
            return {'signal': 'UNWINDING', 'change': chg}
        return {'signal': 'STABLE', 'change': chg}

    def _analyze_china(self) -> Dict[str, Any]:
        chg = self._get_change('CHINA')
        if chg < -5.0:
            return {'signal': 'CRASHING', 'change': chg}
        elif chg > 5.0:
            return {'signal': 'SURGING', 'change': chg}
        return {'signal': 'NORMAL', 'change': chg}

    def _analyze_emerging(self) -> Dict[str, Any]:
        chg = self._get_change('EMERGING')
        if chg < -4.0:
            return {'signal': 'WEAK', 'change': chg}
        return {'signal': 'STABLE', 'change': chg}

    def _analyze_europe(self) -> Dict[str, Any]:
        chg = self._get_change('EUROPE')
        if chg < -4.0:
            return {'signal': 'CRASHING', 'change': chg}
        return {'signal': 'NORMAL', 'change': chg}

def get_global_macro_analyzer() -> GlobalMacroAnalyzer:
    return GlobalMacroAnalyzer()

def get_global_macro_signal() -> GlobalMacroSignal:
    return GlobalMacroAnalyzer().analyze()
