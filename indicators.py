"""
Advanced Technical Indicators
==============================
Comprehensive indicator library for entry/exit signals.

Indicators:
1. VWAP - Institutional price reference
2. RSI - Relative Strength Index
3. MFI - Money Flow Index
4. ATR - Average True Range
5. ADX - Average Directional Index (Trend Strength)
6. OBV - On Balance Volume
7. Bollinger Bands - Volatility bands
8. MACD - Moving Average Convergence Divergence
9. Stochastic RSI - Fast momentum oscillator
10. Volume Profile - Price/Volume relationship
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class BollingerBands:
    """Bollinger Bands result"""
    upper: float
    middle: float
    lower: float
    percent_b: float  # Position within bands (0-1)
    bandwidth: float  # Volatility measure


@dataclass
class MACDResult:
    """MACD calculation result"""
    macd: float
    signal: float
    histogram: float
    is_bullish: bool  # MACD > Signal
    cross_up: bool    # Just crossed above
    cross_down: bool  # Just crossed below


@dataclass
class IndicatorSummary:
    """Summary of all indicators for a symbol"""
    vwap: float
    rsi: float
    mfi: float
    atr: float
    adx: float
    obv_trend: str  # "UP", "DOWN", "NEUTRAL"
    bollinger: BollingerBands
    macd: MACDResult
    stoch_rsi: float
    trend_strength: str  # "STRONG", "MODERATE", "WEAK"
    
    @property
    def entry_score(self) -> int:
        """Calculate entry signal score (0-100)"""
        score = 0
        
        # RSI: 40-60 = neutral, <40 = oversold (good for entry)
        if self.rsi < 40:
            score += 20
        elif self.rsi < 50:
            score += 10
        
        # MFI: <80 = not overbought
        if self.mfi < 70:
            score += 15
        elif self.mfi < 80:
            score += 10
        
        # ADX: Strong trend = good
        if self.adx > 25:
            score += 20
        elif self.adx > 20:
            score += 10
        
        # Bollinger: Near lower band = good entry
        if self.bollinger.percent_b < 0.3:
            score += 15
        elif self.bollinger.percent_b < 0.5:
            score += 10
        
        # MACD: Bullish
        if self.macd.is_bullish:
            score += 15
        if self.macd.cross_up:
            score += 10
        
        # Stochastic RSI: Oversold
        if self.stoch_rsi < 0.3:
            score += 15
        elif self.stoch_rsi < 0.5:
            score += 5
        
        return min(100, score)


# ==============================================
# Basic Indicators
# ==============================================

def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """Volume Weighted Average Price"""
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    cumulative_tp_vol = (typical_price * df['Volume']).cumsum()
    cumulative_vol = df['Volume'].cumsum()
    return cumulative_tp_vol / cumulative_vol


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index"""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    
    rs = avg_gain / avg_loss.replace(0, 1)
    return 100 - (100 / (1 + rs))


def calculate_mfi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Money Flow Index"""
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    money_flow = typical_price * df['Volume']
    
    delta = typical_price.diff()
    positive_flow = money_flow.where(delta > 0, 0.0)
    negative_flow = money_flow.where(delta < 0, 0.0)
    
    positive_mf = positive_flow.rolling(window=period).sum()
    negative_mf = negative_flow.rolling(window=period).sum()
    
    mfr = positive_mf / negative_mf.replace(0, 1)
    return 100 - (100 / (1 + mfr))


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range"""
    high = df['High']
    low = df['Low']
    close = df['Close'].shift(1)
    
    tr1 = high - low
    tr2 = abs(high - close)
    tr3 = abs(low - close)
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


# ==============================================
# Advanced Indicators
# ==============================================

def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Average Directional Index - Trend Strength
    
    Interpretation:
    - ADX > 25: Strong trend
    - ADX 20-25: Moderate trend
    - ADX < 20: Weak/No trend
    """
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    # Calculate +DM and -DM
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    
    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Smoothed values
    atr = tr.ewm(span=period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)
    
    # DX and ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, 1)
    adx = dx.ewm(span=period, adjust=False).mean()
    
    return adx


def calculate_obv(df: pd.DataFrame) -> Tuple[pd.Series, str]:
    """
    On Balance Volume
    Returns: (OBV series, trend direction)
    """
    close = df['Close']
    volume = df['Volume']
    
    obv = (np.sign(close.diff()) * volume).cumsum()
    
    # Determine trend (compare OBV to 20-period SMA)
    obv_sma = obv.rolling(20).mean()
    
    if len(obv) >= 20:
        # Use absolute distance threshold to handle negative OBV values correctly
        threshold = abs(obv_sma.iloc[-1]) * 0.02
        if obv.iloc[-1] > obv_sma.iloc[-1] + threshold:
            trend = "UP"
        elif obv.iloc[-1] < obv_sma.iloc[-1] - threshold:
            trend = "DOWN"
        else:
            trend = "NEUTRAL"
    else:
        trend = "NEUTRAL"
    
    return obv, trend


def calculate_bollinger(close: pd.Series, period: int = 20, 
                       std_dev: float = 2.0) -> BollingerBands:
    """
    Bollinger Bands
    
    %B Interpretation:
    - %B > 1: Price above upper band (overbought)
    - %B < 0: Price below lower band (oversold)
    - %B = 0.5: Price at middle band
    """
    middle = close.rolling(period).mean()
    std = close.rolling(period).std()
    
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    
    current_close = close.iloc[-1]
    current_upper = upper.iloc[-1]
    current_lower = lower.iloc[-1]
    current_middle = middle.iloc[-1]
    
    # %B calculation
    band_range = current_upper - current_lower
    if band_range > 0:
        percent_b = (current_close - current_lower) / band_range
    else:
        percent_b = 0.5
    
    # Bandwidth (volatility)
    bandwidth = band_range / current_middle if current_middle > 0 else 0
    
    return BollingerBands(
        upper=current_upper,
        middle=current_middle,
        lower=current_lower,
        percent_b=percent_b,
        bandwidth=bandwidth
    )


def calculate_bb_squeeze(df: pd.DataFrame,
                         bb_period: int = 20,
                         bb_std: float = 2.0,
                         lookback: int = 20,
                         threshold: float = 0.25) -> dict:
    """
    Bollinger Band Squeeze Detector
    ================================
    볼린저밴드 폭이 N일 중 하위 X분위이면 스퀴즈 상태 (에너지 응축).
    스퀴즈 해제(폭 확장 시작)는 큰 방향성 이동의 전조.

    Returns:
        dict with keys:
          is_squeezing (bool): 현재 스퀴즈 상태
          is_releasing (bool): 스퀴즈 직후 해제 시작 (진입 신호)
          bandwidth (float): 현재 밴드폭
          bandwidth_pct (float): N일 분위 (0=최저, 1=최고)
          direction (str): 해제 방향 "UP" / "DOWN" / "NEUTRAL"
    """
    close = df['Close']
    if len(close) < max(bb_period, lookback) + 5:
        return {
            'is_squeezing': False, 'is_releasing': False,
            'bandwidth': 0.0, 'bandwidth_pct': 0.5, 'direction': 'NEUTRAL'
        }

    # 볼린저밴드 폭 시계열 계산
    middle = close.rolling(bb_period).mean()
    std = close.rolling(bb_period).std()
    upper = middle + std * bb_std
    lower = middle - std * bb_std
    bandwidth_series = (upper - lower) / middle.replace(0, 1)

    # 현재 밴드폭
    current_bw = float(bandwidth_series.iloc[-1])
    prev_bw    = float(bandwidth_series.iloc[-2]) if len(bandwidth_series) > 1 else current_bw

    # N일 분위 계산
    recent = bandwidth_series.dropna().iloc[-lookback:]
    if len(recent) < 5:
        return {
            'is_squeezing': False, 'is_releasing': False,
            'bandwidth': current_bw, 'bandwidth_pct': 0.5, 'direction': 'NEUTRAL'
        }

    rank = float((recent < current_bw).mean())  # 현재값이 recent 중 몇 분위인지

    is_squeezing = rank <= threshold             # 하위 25% → 스퀴즈
    is_releasing = is_squeezing and current_bw > prev_bw  # 스퀴즈이면서 폭 확장 시작

    # 해제 방향: 최근 종가가 중간밴드 위면 UP, 아래면 DOWN
    current_close = float(close.iloc[-1])
    current_mid   = float(middle.iloc[-1])
    if is_releasing:
        direction = 'UP' if current_close > current_mid else 'DOWN'
    else:
        direction = 'NEUTRAL'

    return {
        'is_squeezing':  is_squeezing,
        'is_releasing':  is_releasing,
        'bandwidth':     current_bw,
        'bandwidth_pct': rank,
        'direction':     direction,
    }


def calculate_relative_strength(stock_close: pd.Series,
                                 spy_close: pd.Series,
                                 period: int = 5) -> float:
    """
    SPY 대비 상대강도 계산 (최근 N일)
    양수 = SPY보다 강함, 음수 = SPY보다 약함
    Returns: relative_strength (float, %)
    """
    if len(stock_close) < period + 1 or len(spy_close) < period + 1:
        return 0.0
    try:
        stock_ret = (float(stock_close.iloc[-1]) / float(stock_close.iloc[-period]) - 1) * 100
        spy_ret   = (float(spy_close.iloc[-1])   / float(spy_close.iloc[-period])   - 1) * 100
        return round(stock_ret - spy_ret, 3)
    except Exception:
        return 0.0


def calculate_macd(close: pd.Series, fast: int = 12, slow: int = 26, 
                   signal: int = 9) -> MACDResult:
    """
    MACD - Moving Average Convergence Divergence
    
    Signals:
    - MACD > Signal: Bullish
    - MACD crosses above Signal: Buy signal
    - MACD crosses below Signal: Sell signal
    """
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    current_macd = macd_line.iloc[-1]
    current_signal = signal_line.iloc[-1]
    current_hist = histogram.iloc[-1]
    
    # Check for crossovers
    prev_macd = macd_line.iloc[-2] if len(macd_line) > 1 else current_macd
    prev_signal = signal_line.iloc[-2] if len(signal_line) > 1 else current_signal
    
    cross_up = (prev_macd <= prev_signal) and (current_macd > current_signal)
    cross_down = (prev_macd >= prev_signal) and (current_macd < current_signal)
    
    return MACDResult(
        macd=current_macd,
        signal=current_signal,
        histogram=current_hist,
        is_bullish=current_macd > current_signal,
        cross_up=cross_up,
        cross_down=cross_down
    )


def calculate_stochastic_rsi(close: pd.Series, rsi_period: int = 14, 
                             stoch_period: int = 14) -> pd.Series:
    """
    Stochastic RSI - Fast momentum oscillator
    
    Interpretation:
    - StochRSI > 0.8: Overbought
    - StochRSI < 0.2: Oversold
    """
    rsi = calculate_rsi(close, rsi_period)
    
    min_rsi = rsi.rolling(stoch_period).min()
    max_rsi = rsi.rolling(stoch_period).max()
    
    stoch_rsi = (rsi - min_rsi) / (max_rsi - min_rsi).replace(0, 1)
    
    return stoch_rsi


# ==============================================
# Main Analysis Function
# ==============================================

def analyze_all(df: pd.DataFrame) -> Optional[IndicatorSummary]:
    """
    Calculate all indicators for a dataframe
    
    Returns IndicatorSummary with all values
    """
    if len(df) < 30:
        return None
    
    close = df['Close']
    
    # Basic indicators
    vwap = calculate_vwap(df)
    rsi = calculate_rsi(close)
    mfi = calculate_mfi(df)
    atr = calculate_atr(df)
    
    # Advanced indicators
    adx = calculate_adx(df)
    obv, obv_trend = calculate_obv(df)
    bollinger = calculate_bollinger(close)
    macd = calculate_macd(close)
    stoch_rsi = calculate_stochastic_rsi(close)
    
    # Determine trend strength from ADX
    current_adx = adx.iloc[-1]
    if current_adx > 25:
        trend_strength = "STRONG"
    elif current_adx > 20:
        trend_strength = "MODERATE"
    else:
        trend_strength = "WEAK"
    
    return IndicatorSummary(
        vwap=vwap.iloc[-1],
        rsi=rsi.iloc[-1],
        mfi=mfi.iloc[-1],
        atr=atr.iloc[-1],
        adx=current_adx,
        obv_trend=obv_trend,
        bollinger=bollinger,
        macd=macd,
        stoch_rsi=stoch_rsi.iloc[-1],
        trend_strength=trend_strength
    )


if __name__ == "__main__":
    import yfinance as yf
    
    print("Testing Advanced Indicators...")
    
    # Fetch sample data
    data = yf.download("AMD", period="1mo", interval="1h", progress=False)
    
    if not data.empty:
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        
        result = analyze_all(data)
        
        if result:
            print(f"\n{'='*50}")
            print(f"AMD Indicator Summary")
            print(f"{'='*50}")
            print(f"ENTRY SCORE: {result.entry_score}/100")
            print(f"Stochastic RSI: {result.stoch_rsi:.2f}")
            print(f"{'='*50}")
