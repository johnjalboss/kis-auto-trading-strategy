"""
Alpha Signal Generator
========================
Generate high-conviction alpha signals.
Combines multiple factors for maximum edge.
"""

from dataclasses import dataclass
from typing import List, Optional
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class AlphaSignal:
    symbol: str
    
    # Alpha factors
    momentum_alpha: float      # 12-1 momentum
    reversal_alpha: float      # Short-term mean reversion
    quality_alpha: float       # Trend + vol quality
    value_alpha: float         # RSI oversold/overbought
    
    # Combined
    total_alpha: float
    alpha_rank: int            # 1 = best
    
    # Signal
    signal_strength: str       # "STRONG", "MEDIUM", "WEAK"
    direction: str             # "LONG", "SHORT", "NEUTRAL"
    conviction: int            # 0-100
    
    # Entry optimization
    optimal_entry: float
    ideal_stop: float
    ideal_target: float
    
    details: List[str]


class AlphaGenerator:
    """
    Multi-Factor Alpha Generator
    
    Factors:
    1. Momentum (40%): 6M return, skip last month
    2. Reversal (20%): 5-day mean reversion
    3. Quality (25%): Trend strength + low vol
    4. Value (15%): RSI extremes
    
    Best signals when multiple factors align!
    """
    
    WEIGHTS = {
        'momentum': 0.40,
        'reversal': 0.20,
        'quality': 0.25,
        'value': 0.15
    }
    
    def __init__(self):
        pass
    
    def generate(self, symbol: str) -> AlphaSignal:
        df = self._fetch_data(symbol)
        
        if df is None or len(df) < 130:
            return self._neutral_signal(symbol)
        
        close = df['Close']
        volume = df['Volume']
        details = []
        
        # 1. Momentum Alpha (6M return, skip last month)
        if len(close) >= 126:
            mom_6m = (close.iloc[-21] / close.iloc[-126] - 1) * 100
        else:
            mom_6m = 0
        
        momentum_alpha = np.clip(mom_6m / 20, -1, 1)  # Normalize
        
        if momentum_alpha > 0.5:
            details.append(f"STRONG_MOM:{mom_6m:.1f}%")
        
        # 2. Reversal Alpha (5-day mean reversion)
        ret_5d = (close.iloc[-1] / close.iloc[-5] - 1) * 100
        
        # Oversold = positive alpha (expect bounce)
        if ret_5d < -3:
            reversal_alpha = min(1, abs(ret_5d) / 5)
            details.append(f"OVERSOLD:{ret_5d:.1f}%")
        elif ret_5d > 3:
            reversal_alpha = -min(1, ret_5d / 5)
            details.append(f"OVERBOUGHT:{ret_5d:.1f}%")
        else:
            reversal_alpha = 0
        
        # 3. Quality Alpha (trend + low volatility)
        sma50 = close.rolling(50).mean().iloc[-1]
        sma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else sma50
        
        trend_quality = 1 if close.iloc[-1] > sma50 > sma200 else (-1 if close.iloc[-1] < sma50 < sma200 else 0)
        
        returns = close.pct_change()
        vol = returns.tail(20).std() * np.sqrt(252)
        vol_quality = 1 if vol < 0.25 else (0 if vol < 0.40 else -0.5)
        
        quality_alpha = (trend_quality * 0.7 + vol_quality * 0.3)
        
        if trend_quality > 0:
            details.append("UPTREND")
        
        # 4. Value Alpha (RSI)
        rsi = self._calculate_rsi(close)
        
        if rsi < 30:
            value_alpha = 1
            details.append(f"RSI_OVERSOLD:{rsi:.0f}")
        elif rsi > 70:
            value_alpha = -1
            details.append(f"RSI_OVERBOUGHT:{rsi:.0f}")
        elif rsi < 40:
            value_alpha = 0.3
        elif rsi > 60:
            value_alpha = -0.3
        else:
            value_alpha = 0
        
        # Combined Alpha
        total = (
            momentum_alpha * self.WEIGHTS['momentum'] +
            reversal_alpha * self.WEIGHTS['reversal'] +
            quality_alpha * self.WEIGHTS['quality'] +
            value_alpha * self.WEIGHTS['value']
        )
        
        # Signal strength
        if abs(total) > 0.6:
            strength = "STRONG"
        elif abs(total) > 0.3:
            strength = "MEDIUM"
        else:
            strength = "WEAK"
        
        # Direction
        if total > 0.2:
            direction = "LONG"
        elif total < -0.2:
            direction = "SHORT"
        else:
            direction = "NEUTRAL"
        
        # Conviction (0-100)
        conviction = int(min(100, abs(total) * 100))
        
        # Entry optimization
        current = float(close.iloc[-1])
        atr = self._calculate_atr(df)
        
        if direction == "LONG":
            optimal_entry = current  # Market order
            ideal_stop = current - (1.5 * atr)
            ideal_target = current + (3 * atr)
        elif direction == "SHORT":
            optimal_entry = current
            ideal_stop = current + (1.5 * atr)
            ideal_target = current - (3 * atr)
        else:
            optimal_entry = current
            ideal_stop = current * 0.97
            ideal_target = current * 1.03
        
        return AlphaSignal(
            symbol=symbol,
            momentum_alpha=momentum_alpha,
            reversal_alpha=reversal_alpha,
            quality_alpha=quality_alpha,
            value_alpha=value_alpha,
            total_alpha=total,
            alpha_rank=0,  # Set when comparing multiple
            signal_strength=strength,
            direction=direction,
            conviction=conviction,
            optimal_entry=optimal_entry,
            ideal_stop=ideal_stop,
            ideal_target=ideal_target,
            details=details
        )
    
    def rank_symbols(self, symbols: List[str]) -> List[AlphaSignal]:
        """Rank multiple symbols by alpha"""
        signals = []
        
        for sym in symbols:
            sig = self.generate(sym)
            signals.append(sig)
        
        # Sort by total alpha (descending)
        signals.sort(key=lambda x: x.total_alpha, reverse=True)
        
        # Assign ranks
        for i, sig in enumerate(signals):
            sig.alpha_rank = i + 1
        
        return signals
    
    def _calculate_rsi(self, close: pd.Series, period: int = 14) -> float:
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss.replace(0, 1)
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        h, l, c = df['High'], df['Low'], df['Close']
        tr = pd.DataFrame({
            'hl': h - l,
            'hc': abs(h - c.shift()),
            'lc': abs(l - c.shift())
        }).max(axis=1)
        return float(tr.rolling(period).mean().iloc[-1])
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        try:
            df = yf.download(symbol, period='1y', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return None
    
    def _neutral_signal(self, symbol: str) -> AlphaSignal:
        return AlphaSignal(symbol, 0, 0, 0, 0, 0, 99, "WEAK", "NEUTRAL", 0, 0, 0, 0, [])


def get_alpha_generator() -> AlphaGenerator:
    return AlphaGenerator()


if __name__ == "__main__":
    print("Testing AlphaGenerator...")
    
    gen = AlphaGenerator()
    
    symbols = ["AAPL", "NVDA", "TSLA", "MSFT", "AMD"]
    ranked = gen.rank_symbols(symbols)
    
    print(f"\n{'='*60}")
    print("ALPHA RANKING")
    print('='*60)
    
    for sig in ranked:
        print(f"\n#{sig.alpha_rank} {sig.symbol}")
        print(f"  Total Alpha: {sig.total_alpha:+.2f}")
        print(f"  Momentum: {sig.momentum_alpha:+.2f}")
        print(f"  Reversal: {sig.reversal_alpha:+.2f}")
        print(f"  Quality: {sig.quality_alpha:+.2f}")
        print(f"  Value: {sig.value_alpha:+.2f}")
        print(f"  Signal: {sig.signal_strength} {sig.direction}")
        print(f"  Conviction: {sig.conviction}%")
        print(f"  Details: {sig.details}")
