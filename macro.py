"""
Enhanced Macro Analyzer
========================
Multi-factor macro regime detection for optimal position sizing.

Factors:
1. VIX - Volatility regime
2. TNX - Interest rate pressure
3. DXY - Dollar strength
4. HYG/LQD - Credit risk appetite
5. Gold - Safe haven demand
6. Put/Call Ratio - Options sentiment
7. Advance/Decline - Market breadth
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict
from enum import Enum
import pandas as pd
import numpy as np
import kis_data as yf  # KIS API drop-in replacement
from loguru import logger
import threading
import time
import concurrent.futures

import config

# Global caches to prevent thundering herd and duplicate downloads
_macro_cache = {}
_macro_cache_time = 0.0
_macro_lock = threading.Lock()


class MarketRegime(Enum):
    """Market regime classification"""
    RISK_ON = "RISK_ON"
    RISK_OFF = "RISK_OFF"
    NEUTRAL = "NEUTRAL"


@dataclass
class MacroSignal:
    """Individual macro signal"""
    name: str
    value: float
    threshold: float
    is_risk_off: bool
    weight: float = 1.0
    
    @property
    def score(self) -> float:
        """Return weighted score (negative = risk off)"""
        return -self.weight if self.is_risk_off else self.weight


@dataclass
class MacroState:
    """Complete macro analysis result"""
    regime: MarketRegime
    betting_ratio: float
    score: float  # -100 to +100
    signals: List[MacroSignal] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class MacroAnalyzer:
    """
    Enhanced Macro Regime Analyzer
    
    Scoring System (Total: -100 to +100):
    - VIX Regime: ±25 points
    - TNX Pressure: ±15 points  
    - DXY Strength: ±15 points
    - HYG/LQD Ratio: ±15 points
    - Gold Flight: ±10 points
    - Put/Call Ratio: ±10 points
    - Advance/Decline: ±10 points
    
    Position Sizing:
    - Score > 50: 100% (Full Risk)
    - Score 20-50: 70% (Moderate)
    - Score -20 to 20: 50% (Neutral)
    - Score -50 to -20: 30% (Cautious)
    - Score < -50: 10% (Defensive)
    """
    
    # Tickers — KIS API에서 사용 가능한 종목만 사용
    # 지수(^VIX, ^TNX)는 KIS 미지원 → ETF 프록시 사용
    TICKERS = {
        "vix": "VIXY",      # VIX ETF proxy (ProShares VIX Short-Term)
        "tnx": "TLT",       # 20Y+ Treasury ETF (역상관 → 금리 상승 시 하락)
        "dxy": "UUP",       # Dollar Bull ETF (달러 강세 추적)
        "hyg": "HYG",
        "lqd": "LQD",
        "gld": "GLD",
        "spy": "SPY",
    }
    
    # Weights
    WEIGHTS = {
        "vix": 25,
        "tnx": 15,
        "dxy": 15,
        "hyg_lqd": 15,
        "gold": 10,
        "put_call": 10,
        "breadth": 10,
    }
    
    def __init__(self, lookback: int = 60):
        self.lookback = lookback
        self._cache: Dict[str, pd.DataFrame] = {}
        self._cache_time: Optional[datetime] = None
    
    def _fetch_data(self) -> bool:
        """Fetch all macro data via KIS API (개별 종목 조회)"""
        global _macro_cache, _macro_cache_time
        
        # Check cache (15 min)
        now = time.time()
        if now - _macro_cache_time < 900 and _macro_cache:
            self._cache = _macro_cache.copy()
            return True
            
        # Double-checked locking pattern inside single-flight fetch
        with _macro_lock:
            now = time.time()
            if now - _macro_cache_time < 900 and _macro_cache:
                self._cache = _macro_cache.copy()
                return True
                
            try:
                temp_cache = {}
                def _fetch_ticker(name, ticker):
                    try:
                        df = yf.download(ticker, period=f"{self.lookback + 10}d",
                                        progress=False, auto_adjust=True)
                        if df is not None and not df.empty and 'Close' in df.columns:
                            return name, df['Close'].dropna()
                        else:
                            logger.debug("No data for macro ticker: {}", ticker)
                    except Exception as e:
                        logger.debug("Failed to fetch {}: {}", ticker, e)
                    return None

                # Parallel fetch across 7 macro assets
                with concurrent.futures.ThreadPoolExecutor(max_workers=7) as executor:
                    futures = [executor.submit(_fetch_ticker, name, ticker) for name, ticker in self.TICKERS.items()]
                    for fut in concurrent.futures.as_completed(futures):
                        res = fut.result()
                        if res:
                            name, close_data = res
                            temp_cache[name] = close_data
                            
                if len(temp_cache) > 0:
                    _macro_cache = temp_cache.copy()
                    _macro_cache_time = now
                    self._cache = temp_cache.copy()
                    logger.info("MacroAnalyzer: Macro data fetched: {}/{} tickers in parallel", len(temp_cache), len(self.TICKERS))
                    return True
                return False
                
            except Exception as e:
                logger.error("Macro data fetch failed: {}", e)
                return False
    
    def analyze(self) -> MacroState:
        """Perform complete macro analysis"""
        if not self._fetch_data():
            # [Quant Fail-Safe] 데이터 부재 시 안전을 위해 강제로 RISK_OFF 및 베팅비율 최소화(10%) 선언
            logger.error("🚨 Macro data fetch failed. Fail-safe locked to RISK_OFF.")
            return MacroState(MarketRegime.RISK_OFF, 0.1, -80, [], ["Data unavailable - Fallback to RISK_OFF"])
        
        signals = []
        triggers = []
        
        # 1. VIX Analysis (±25)
        vix_signal = self._analyze_vix()
        if vix_signal:
            signals.append(vix_signal)
            if vix_signal.is_risk_off:
                triggers.append(f"VIX:{vix_signal.value:.0f}")
        
        # 2. TNX Analysis (±15)
        tnx_signal = self._analyze_tnx()
        if tnx_signal:
            signals.append(tnx_signal)
            if tnx_signal.is_risk_off:
                triggers.append(f"TNX:{tnx_signal.value:+.1%}")
        
        # 3. DXY Analysis (±15)
        dxy_signal = self._analyze_dxy()
        if dxy_signal:
            signals.append(dxy_signal)
            if dxy_signal.is_risk_off:
                triggers.append(f"DXY:{dxy_signal.value:+.1%}")
        
        # 4. HYG/LQD Credit Spread (±15)
        credit_signal = self._analyze_credit()
        if credit_signal:
            signals.append(credit_signal)
            if credit_signal.is_risk_off:
                triggers.append("CREDIT")
        
        # 5. Gold Flight (±10)
        gold_signal = self._analyze_gold()
        if gold_signal:
            signals.append(gold_signal)
            if gold_signal.is_risk_off:
                triggers.append("GOLD")
        
        # 6. Put/Call Ratio (±10)
        pc_signal = self._analyze_put_call()
        if pc_signal:
            signals.append(pc_signal)
            if pc_signal.is_risk_off:
                triggers.append("PUT/CALL")
        
        # 7. Market Breadth (±10)
        breadth_signal = self._analyze_breadth()
        if breadth_signal:
            signals.append(breadth_signal)
            if breadth_signal.is_risk_off:
                triggers.append("BREADTH")
        
        # Calculate total score
        total_score = sum(s.score for s in signals)
        
        # Determine regime and betting ratio
        if total_score > 50:
            regime = MarketRegime.RISK_ON
            betting = 1.0
        elif total_score > 20:
            regime = MarketRegime.RISK_ON
            betting = 0.7
        elif total_score > -20:
            regime = MarketRegime.NEUTRAL
            betting = 0.5
        elif total_score > -50:
            regime = MarketRegime.RISK_OFF
            betting = 0.3
        else:
            regime = MarketRegime.RISK_OFF
            betting = 0.1
        
        logger.info("Macro Score: {:.0f} | Regime: {} | Betting: {:.0%}",
                   total_score, regime.value, betting)
        
        return MacroState(
            regime=regime,
            betting_ratio=betting,
            score=total_score,
            signals=signals,
            triggers=triggers
        )
    
    def _analyze_vix(self) -> Optional[MacroSignal]:
        """VIX via VIXY proxy: VIXY 상승 = 변동성 증가 = Risk Off"""
        if "vix" not in self._cache:
            return None
        
        vixy = self._cache["vix"]  # VIXY ETF (VIX 추종)
        if len(vixy) < min(self.lookback, 20):
            return None
        
        current = vixy.iloc[-1]
        lookback = min(self.lookback, len(vixy))
        sma = vixy.tail(lookback).mean()
        
        # VIXY > SMA = 변동성 증가 = Risk Off
        ratio = current / sma if sma > 0 else 1.0
        
        if ratio > 1.2:
            return MacroSignal("VIX", current, sma, True, self.WEIGHTS["vix"])
        elif ratio > 1.0:
            return MacroSignal("VIX", current, sma, True, self.WEIGHTS["vix"] * 0.5)
        else:
            return MacroSignal("VIX", current, sma, False, self.WEIGHTS["vix"])
    
    def _analyze_tnx(self) -> Optional[MacroSignal]:
        """TNX (10Y Yield) via TLT proxy: TLT 하락 = 금리 상승 = Risk Off"""
        if "tnx" not in self._cache:
            return None
        
        tlt = self._cache["tnx"]  # TLT ETF (inverse of yield)
        if len(tlt) < 5:
            return None
        
        # TLT 하락 = 금리 상승 → 부호 반전
        daily_change = -((tlt.iloc[-1] - tlt.iloc[-2]) / tlt.iloc[-2])
        
        # Sharp yield spike (TLT drop > 0.8%) = Risk Off
        if daily_change > 0.008:
            return MacroSignal("TNX", daily_change, 0.008, True, self.WEIGHTS["tnx"])
        elif daily_change > 0.004:
            return MacroSignal("TNX", daily_change, 0.004, True, self.WEIGHTS["tnx"] * 0.5)
        else:
            return MacroSignal("TNX", daily_change, 0.004, False, self.WEIGHTS["tnx"])
    
    def _analyze_dxy(self) -> Optional[MacroSignal]:
        """DXY (Dollar) Analysis: Strong dollar = Risk Off"""
        if "dxy" not in self._cache:
            return None
        
        dxy = self._cache["dxy"]
        if len(dxy) < 5:
            return None
        
        daily_change = (dxy.iloc[-1] - dxy.iloc[-2]) / dxy.iloc[-2]
        
        # Strong dollar rally (>0.5%) = Risk Off
        if daily_change > 0.005:
            return MacroSignal("DXY", daily_change, 0.005, True, self.WEIGHTS["dxy"])
        elif daily_change > 0.003:
            return MacroSignal("DXY", daily_change, 0.003, True, self.WEIGHTS["dxy"] * 0.5)
        else:
            return MacroSignal("DXY", daily_change, 0.003, False, self.WEIGHTS["dxy"])
    
    def _analyze_credit(self) -> Optional[MacroSignal]:
        """HYG/LQD Ratio: Credit Risk Appetite"""
        if "hyg" not in self._cache or "lqd" not in self._cache:
            return None
        
        hyg = self._cache["hyg"]
        lqd = self._cache["lqd"]
        
        if len(hyg) < self.lookback or len(lqd) < self.lookback:
            return None
        
        # HYG/LQD ratio - higher = more risk appetite
        ratio = hyg / lqd
        current_ratio = ratio.iloc[-1]
        sma_ratio = ratio.tail(self.lookback).mean()
        
        # Ratio falling below SMA = Risk Off (flight to quality)
        if current_ratio < sma_ratio * 0.98:
            return MacroSignal("HYG/LQD", current_ratio, sma_ratio, True, self.WEIGHTS["hyg_lqd"])
        else:
            return MacroSignal("HYG/LQD", current_ratio, sma_ratio, False, self.WEIGHTS["hyg_lqd"])
    
    def _analyze_gold(self) -> Optional[MacroSignal]:
        """Gold Analysis: Safe Haven Demand"""
        if "gld" not in self._cache:
            return None
        
        gld = self._cache["gld"]
        if len(gld) < 20:
            return None
        
        # Gold outperforming (5-day vs 20-day momentum)
        short_mom = (gld.iloc[-1] - gld.iloc[-5]) / gld.iloc[-5]
        long_mom = (gld.iloc[-1] - gld.iloc[-20]) / gld.iloc[-20]
        
        # Sharp gold rally = Flight to safety = Risk Off
        if short_mom > 0.02 and short_mom > long_mom:
            return MacroSignal("GOLD", short_mom, 0.02, True, self.WEIGHTS["gold"])
        else:
            return MacroSignal("GOLD", short_mom, 0.02, False, self.WEIGHTS["gold"])
    
    def _analyze_put_call(self) -> Optional[MacroSignal]:
        """Put/Call Ratio Estimation using VIX/VIX3M relationship"""
        # Since we don't have direct Put/Call data, estimate from VIX term structure
        if "vix" not in self._cache:
            return None
        
        vix = self._cache["vix"]
        if len(vix) < 10:
            return None
        
        # Use VIX 5-day momentum as proxy for fear
        vix_mom = (vix.iloc[-1] - vix.iloc[-5]) / vix.iloc[-5]
        
        # Rising VIX = More puts being bought = Fear = Risk Off
        if vix_mom > 0.15:
            return MacroSignal("P/C_PROXY", vix_mom, 0.15, True, self.WEIGHTS["put_call"])
        elif vix_mom > 0.08:
            return MacroSignal("P/C_PROXY", vix_mom, 0.08, True, self.WEIGHTS["put_call"] * 0.5)
        else:
            return MacroSignal("P/C_PROXY", vix_mom, 0.08, False, self.WEIGHTS["put_call"])
    
    def _analyze_breadth(self) -> Optional[MacroSignal]:
        """Market Breadth: SPY momentum as proxy"""
        if "spy" not in self._cache:
            return None
        
        spy = self._cache["spy"]
        if len(spy) < self.lookback:
            return None
        
        # Compare short-term to long-term performance
        short_perf = (spy.iloc[-1] - spy.iloc[-5]) / spy.iloc[-5]
        long_perf = (spy.iloc[-1] - spy.iloc[-20]) / spy.iloc[-20]
        
        # Weakening breadth = short-term lagging
        if short_perf < -0.02 and short_perf < long_perf:
            return MacroSignal("BREADTH", short_perf, -0.02, True, self.WEIGHTS["breadth"])
        else:
            return MacroSignal("BREADTH", short_perf, -0.02, False, self.WEIGHTS["breadth"])


# Global instance
_analyzer = None

def get_macro_analyzer() -> MacroAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = MacroAnalyzer()
    return _analyzer


def get_macro_score() -> float:
    """Convenience wrapper: returns just the numeric score (-100 to +100)"""
    try:
        analyzer = get_macro_analyzer()
        result = analyzer.analyze()
        return result.score
    except Exception as e:
        logger.error("get_macro_score failed: {}", e)
        return 0


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="DEBUG", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing Enhanced MacroAnalyzer...")
    
    analyzer = MacroAnalyzer()
    result = analyzer.analyze()
    
    print(f"\n{'='*50}")
    print(f"Score: {result.score:.0f}")
    print(f"Regime: {result.regime.value}")
    print(f"Betting: {result.betting_ratio:.0%}")
    print(f"Triggers: {result.triggers}")
    print(f"{'='*50}")
    
    print("\nSignal Details:")
    for sig in result.signals:
        status = "⚠️" if sig.is_risk_off else "✅"
        print(f"  {status} {sig.name}: {sig.value:.4f} (score: {sig.score:+.0f})")
