"""
Signal Aggregator - Advanced Signal Integration Engine
======================================================
Performs 6 advanced analyses to calculate a bonus score for trading signals.

Analysis Items:
1. Divergence (RSI/MACD)           +/-12
2. Candlestick Patterns             +/-10
3. Accumulation (Wyckoff)           +/-8
4. S/R Position (Support/Resist)    +/-8
5. Volume Surge                     +/-5
6. Institutional / Macro Context    +/-12

Total Bonus Range: -55 to +55
"""

from dataclasses import dataclass, field
from typing import List, Optional
import pandas as pd
import numpy as np
import concurrent.futures
from loguru import logger

@dataclass
class AggregatedSignal:
    """Aggregated signal result with detailed scores and bonus."""
    bonus_score: int = 0
    details: List[str] = field(default_factory=list)
    
    # Individual scores
    divergence_score: int = 0     # +/-12
    candlestick_score: int = 0    # +/-10
    accumulation_score: int = 0   # +/-8
    sr_score: int = 0             # +/-8
    volume_score: int = 0         # +/-5
    institutional_score: int = 0  # +/-12


class SignalAggregator:
    """
    Enhances base signals with advanced technical and institutional analysis.
    Designed for daily OHLCV data. Returns a bonus score to be added to confidence.
    """
    
    def analyze(self, df: pd.DataFrame, symbol: str = "GLOBAL") -> AggregatedSignal:
        """Runs all 6 analyses and returns aggregated bonus."""
        result = AggregatedSignal()
        
        if df is None or len(df) < 20:
            return result
        
        try:
            # 1. Divergence (+/-12)
            div_score, div_details = self._check_divergence(df)
            result.divergence_score = div_score
            result.bonus_score += div_score
            result.details.extend(div_details)
        except Exception as e:
            logger.debug(f"Divergence analysis failed: {e}")
        
        try:
            # 2. Candlestick (+/-10)
            candle_score, candle_details = self._check_candlestick(df)
            result.candlestick_score = candle_score
            result.bonus_score += candle_score
            result.details.extend(candle_details)
        except Exception as e:
            logger.debug(f"Candlestick analysis failed: {e}")
        
        try:
            # 3. Accumulation / Wyckoff (+/-8)
            acc_score, acc_details = self._check_accumulation(df)
            result.accumulation_score = acc_score
            result.bonus_score += acc_score
            result.details.extend(acc_details)
        except Exception as e:
            logger.debug(f"Accumulation analysis failed: {e}")
        
        try:
            # 4. S/R Position (+/-8)
            sr_score, sr_details = self._check_sr_position(df)
            result.sr_score = sr_score
            result.bonus_score += sr_score
            result.details.extend(sr_details)
        except Exception as e:
            logger.debug(f"S/R analysis failed: {e}")
            
        try:
            # 5. Volume Surge (+/-5)
            vol_score, vol_details = self._check_volume_surge(df)
            result.volume_score = vol_score
            result.bonus_score += vol_score
            result.details.extend(vol_details)
        except Exception as e:
            logger.debug(f"Volume surge analysis failed: {e}")

        try:
            # 6. Institutional / Macro (+/-12)
            inst_score, inst_details = self._check_institutional(df, symbol)
            result.institutional_score = inst_score
            result.bonus_score += inst_score
            result.details.extend(inst_details)
        except Exception as e:
            logger.debug(f"Institutional analysis failed: {e}")

        try:
            # 7. [INSTITUTIONAL QUANT] Sharpe-Weighted Volatility-Adjusted Momentum (+/-15)
            sharpe_score, sharpe_details = self._check_sharpe_vol_momentum(df)
            result.bonus_score += sharpe_score
            result.details.extend(sharpe_details)
        except Exception as e:
            logger.debug(f"Sharpe Vol Momentum analysis failed: {e}")
        
        # Clamp final score (-60 to +60)
        result.bonus_score = max(-60, min(60, result.bonus_score))
        
        if result.details:
            logger.debug(f"Signal aggregator: bonus={result.bonus_score:+d} {result.details}")
        
        return result
    
    # ===============================================
    # 1. DIVERGENCE (RSI / MACD)
    # ===============================================
    def _check_divergence(self, df: pd.DataFrame) -> tuple:
        """Detects RSI/MACD divergence."""
        score = 0
        details = []
        close = df['Close']
        if len(close) < 30: return 0, []
        
        rsi = self._calc_rsi(close)
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd_hist = (ema12 - ema26) - (ema12 - ema26).ewm(span=9).mean()
        
        rsi_div = self._detect_divergence(close, rsi)
        if rsi_div == "BULLISH":
            score += 8
            details.append("RSI_BULL_DIV")
        elif rsi_div == "BEARISH":
            score -= 8
            details.append("RSI_BEAR_DIV")
        
        macd_div = self._detect_divergence(close, macd_hist)
        if macd_div == "BULLISH":
            score += 4
            details.append("MACD_BULL_DIV")
        elif macd_div == "BEARISH":
            score -= 4
            details.append("MACD_BEAR_DIV")
        
        return max(-12, min(12, score)), details

    def _detect_divergence(self, price: pd.Series, indicator: pd.Series, window: int = 20) -> str:
        price_recent = price.tail(window).values
        ind_recent = indicator.tail(window).values
        if len(price_recent) < 10: return "NONE"
        
        # Find swing point indices in price series
        low_indices = []
        high_indices = []
        for i in range(2, len(price_recent) - 2):
            if (price_recent[i] < price_recent[i-1] and price_recent[i] < price_recent[i-2] and
                price_recent[i] < price_recent[i+1] and price_recent[i] < price_recent[i+2]):
                low_indices.append(i)
            if (price_recent[i] > price_recent[i-1] and price_recent[i] > price_recent[i-2] and
                price_recent[i] > price_recent[i+1] and price_recent[i] > price_recent[i+2]):
                high_indices.append(i)
                
        # Compare price and indicator values at the exact same swing indices
        if len(low_indices) >= 2:
            i1, i2 = low_indices[-2], low_indices[-1]
            if price_recent[i2] < price_recent[i1] and ind_recent[i2] > ind_recent[i1]:
                return "BULLISH"
        if len(high_indices) >= 2:
            i1, i2 = high_indices[-2], high_indices[-1]
            if price_recent[i2] > price_recent[i1] and ind_recent[i2] < ind_recent[i1]:
                return "BEARISH"
        return "NONE"

    def _find_swing_points(self, values: np.ndarray, mode: str = "low") -> list:
        points = []
        for i in range(2, len(values) - 2):
            if mode == "low":
                if (values[i] < values[i-1] and values[i] < values[i-2] and
                    values[i] < values[i+1] and values[i] < values[i+2]):
                    points.append(values[i])
            else:
                if (values[i] > values[i-1] and values[i] > values[i-2] and
                    values[i] > values[i+1] and values[i] > values[i+2]):
                    points.append(values[i])
        return points[-3:] if points else []

    # ===============================================
    # 2. CANDLESTICK (+/-10)
    # ===============================================
    def _check_candlestick(self, df: pd.DataFrame) -> tuple:
        score, details = 0, []
        if len(df) < 3: return 0, []
        o, h, l, c = df['Open'].iloc[-1], df['High'].iloc[-1], df['Low'].iloc[-1], df['Close'].iloc[-1]
        body = abs(c - o)
        candle_range = h - l
        if candle_range == 0: return 0, []
        
        lower_shadow = min(o, c) - l
        upper_shadow = h - max(o, c)
        
        if body > 0 and lower_shadow > body * 2 and upper_shadow < body * 0.5:
            score += 6
            details.append("HAMMER")
        if body > 0 and upper_shadow > body * 2 and lower_shadow < body * 0.5:
            score -= 6
            details.append("SHOOTING_STAR")
            
        if len(df) >= 2:
            o1, c1 = df['Open'].iloc[-2], df['Close'].iloc[-2]
            if c1 < o1 and c > o and c > o1 and o < c1:
                score += 8
                details.append("BULL_ENGULF")
            elif c1 > o1 and c < o and c < o1 and o > c1:
                score -= 8
                details.append("BEAR_ENGULF")
        
        return max(-10, min(10, score)), details

    # ===============================================
    # 3. ACCUMULATION / WYCKOFF (+/-8)
    # ===============================================
    def _check_accumulation(self, df: pd.DataFrame) -> tuple:
        score, details = 0, []
        if len(df) < 40: return 0, []
        close, low, high, volume = df['Close'], df['Low'], df['High'], df['Volume']
        recent_high, recent_low = high.tail(20).max(), low.tail(20).min()
        range_size = (recent_high - recent_low) / recent_low if recent_low > 0 else 1
        if range_size > 0.15: return 0, []
        
        prior_close = close.iloc[-40:-20]
        prior_trend = "DOWN" if prior_close.iloc[-1] < prior_close.iloc[0] else "UP"
        
        support = low.tail(20).iloc[:15].min()
        if any(low.tail(5) < support) and close.iloc[-1] > support and prior_trend == "DOWN":
            score += 6
            details.append("SPRING")
            
        resistance = high.tail(20).iloc[:15].max()
        if any(high.tail(5) > resistance) and close.iloc[-1] < resistance and prior_trend == "UP":
            score -= 6
            details.append("UPTHRUST")
            
        return max(-8, min(8, score)), details

    # ===============================================
    # 4. SUPPORT/RESISTANCE POSITION (+/-8)
    # ===============================================
    def _check_sr_position(self, df: pd.DataFrame) -> tuple:
        score, details = 0, []
        if len(df) < 20: return 0, []
        close, high, low = df['Close'], df['High'], df['Low']
        current = float(close.iloc[-1])
        h_prev, l_prev, c_prev = float(high.iloc[-2]), float(low.iloc[-2]), float(close.iloc[-2])
        pivot = (h_prev + l_prev + c_prev) / 3
        s1, r1 = 2 * pivot - h_prev, 2 * pivot - l_prev
        
        if abs(current - s1) / current < 0.02:
            score += 8
            details.append("NEAR_SUPPORT")
        elif abs(current - r1) / current < 0.02:
            score -= 6
            details.append("NEAR_RESISTANCE")
            
        return max(-8, min(8, score)), details

    # ===============================================
    # 5. VOLUME SURGE (+/-5)
    # ===============================================
    def _check_volume_surge(self, df: pd.DataFrame) -> tuple:
        score, details = 0, []
        if len(df) < 20: return 0, []
        avg_vol = df['Volume'].tail(20).mean()
        recent_vol = float(df['Volume'].iloc[-1])
        change = float(df['Close'].iloc[-1] / df['Close'].iloc[-2] - 1) if len(df) >= 2 else 0
        if avg_vol <= 0: return 0, []
        
        ratio = recent_vol / avg_vol
        if ratio > 2.0 and change > 0.01:
            score += 5
            details.append(f"VOL_SURGE:{ratio:.1f}x")
        elif ratio > 2.0 and change < -0.01:
            score -= 5
            details.append(f"VOL_EXIT:{ratio:.1f}x")
        return max(-5, min(5, score)), details

    # ===============================================
    # 6. INSTITUTIONAL & MACRO (+/-12)
    # ===============================================
    def _check_institutional(self, df: pd.DataFrame, symbol: str) -> tuple:
        """Context analysis via institutional modules."""
        score, details = 0, []
        from fx_risk import FXRiskAnalyzer
        from earnings_quality import EarningsQualityScorer
        from estimate_revision import EstimateRevisionAnalyzer
        from short_squeeze import ShortSqueezeMonitor
        from economic_surprise import EconomicSurpriseAnalyzer
        
        analyzers = [
            FXRiskAnalyzer(), EarningsQualityScorer(), EstimateRevisionAnalyzer(),
            ShortSqueezeMonitor(), EconomicSurpriseAnalyzer()
        ]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(a.analyze, df, symbol=symbol): a for a in analyzers}
            done, not_done = concurrent.futures.wait(futures.keys(), timeout=5.0)
            for future in done:
                try:
                    res = future.result()
                    s = res.get('score', 0)
                    sigs = res.get('signals', [])
                    score += s
                    if s > 15: details.append(f"INST_BULL:{sigs[0] if sigs else 'YES'}")
                    elif s < -15: details.append(f"INST_BEAR:{sigs[0] if sigs else 'YES'}")
                except Exception:
                    continue
            for future in not_done:
                future.cancel()
        
        final_score = int(score / 15.0)
        return max(-12, min(12, final_score)), details

    # ===============================================
    # 7. SHARPE-WEIGHTED VOLATILITY-ADJUSTED MOMENTUM
    # ===============================================
    def _check_sharpe_vol_momentum(self, df: pd.DataFrame) -> tuple:
        """Calculates risk-adjusted Sharpe momentum (63-day Sharpe Ratio)."""
        score = 0
        details = []
        if df is None or len(df) < 30:
            return 0, []
        
        try:
            close = df['Close']
            daily_returns = close.pct_change().dropna()
            if len(daily_returns) < 20:
                return 0, []
            
            recent_returns = daily_returns.tail(63)
            mean_ret = recent_returns.mean()
            std_ret = recent_returns.std()
            
            if std_ret > 0:
                ann_sharpe = (mean_ret * 252) / (std_ret * np.sqrt(252))
                if ann_sharpe >= 2.0:
                    score = 15
                    details.append(f"SMOOTH_SHARPE_LEADER:{ann_sharpe:.1f}")
                elif ann_sharpe >= 1.2:
                    score = 8
                    details.append(f"SOLID_SHARPE_UPTREND:{ann_sharpe:.1f}")
                elif ann_sharpe < -0.5:
                    score = -10
                    details.append(f"HIGH_VOL_DOWNTREND:{ann_sharpe:.1f}")
        except Exception:
            pass
            
        return score, details

    # ===============================================
    # UTILITY
    # ===============================================
    def _calc_rsi(self, close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss.replace(0, 1)
        return 100 - (100 / (1 + rs))

_aggregator = None
def get_signal_aggregator() -> SignalAggregator:
    global _aggregator
    if _aggregator is None: _aggregator = SignalAggregator()
    return _aggregator
