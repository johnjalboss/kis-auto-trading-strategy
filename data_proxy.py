"""
Data Proxy for Monkey Patching yfinance
=========================================
This module intercepts calls to `yfinance.download` AND `yfinance.Ticker`
made by 70+ legacy modules and routes them to KIS API data.

Usage:
    Import this at the very top of your entry-point:
    import data_proxy
"""

import yfinance as yf
from kis_data import download as kis_download
from loguru import logger
import pandas as pd
import time

# ============================================================
# PART 1: yf.download() Shim (기존)
# ============================================================

_cache = {}
_cache_expiry = 300  # 5 minutes

_original_yf_download = yf.download
_yf_call_count = 0
_yf_last_reset_time = time.time()
YF_CALL_LIMIT_PER_HOUR = 120  # Safe limit for yfinance fallback calls (KIS-only paths unaffected)

def _safe_original_yf_download(tickers, *args, **kwargs):
    """
    Executes yfinance download with a strict circuit breaker to avoid IP bans.
    """
    global _yf_call_count, _yf_last_reset_time
    now = time.time()
    
    # Reset count every 1 hour (3600 seconds)
    if now - _yf_last_reset_time > 3600:
        _yf_call_count = 0
        _yf_last_reset_time = now
        logger.info("yfinance Circuit Breaker: Hourly counter reset.")
        
    if _yf_call_count >= YF_CALL_LIMIT_PER_HOUR:
        logger.error(f"yfinance Circuit Breaker TRIPPED! Call limit ({YF_CALL_LIMIT_PER_HOUR}/hour) exceeded. Blocking call for {tickers} to protect IP reputation.")
        return pd.DataFrame()
        
    _yf_call_count += 1
    logger.info(f"yfinance proxy call (Count: {_yf_call_count}/{YF_CALL_LIMIT_PER_HOUR}) for {tickers}")
    try:
        return _original_yf_download(tickers, *args, **kwargs)
    except Exception as e:
        logger.error(f"yfinance original download failed for {tickers}: {e}")
        return pd.DataFrame()

def _proxy_download(tickers, *args, **kwargs):
    """
    Intercepts yfinance download requests and routes them to kis_data.download.
    """
    period = kwargs.get('period', '3mo')
    interval = kwargs.get('interval', '1d')
    progress = kwargs.get('progress', False)
    auto_adjust = kwargs.get('auto_adjust', True)
    
    BYPASS_TICKERS = ["KRW=X", "TIP", "HYG", "TLT", "XLI", "XLF"]
    
    if isinstance(tickers, list) and len(tickers) == 1:
        symbol = tickers[0]
    elif isinstance(tickers, str):
        symbol = tickers
    else:
        logger.warning(f"DataProxy: Multiple tickers unsupported by KIS direct proxy. Passing to original yf. {tickers}")
        return _safe_original_yf_download(tickers, *args, **kwargs)

    # Bypass KIS for specific macro/FX tickers
    if any(bt in symbol.upper() for bt in BYPASS_TICKERS):
        logger.debug(f"DataProxy: Bypassing KIS for macro ticker {symbol}")
        return _safe_original_yf_download(tickers, *args, **kwargs)

    # Remove noisy debug traces
    pass
    
    cache_key = f"{symbol}_{period}_{interval}_{auto_adjust}"
    now = time.time()
    if cache_key in _cache:
        cached_df, timestamp = _cache[cache_key]
        if now - timestamp < _cache_expiry:
            return cached_df.copy()
    
    try:
        df = kis_download(tickers=symbol, period=period, interval=interval, 
                          progress=progress, auto_adjust=auto_adjust)
        if df is not None and not df.empty:
            _cache[cache_key] = (df.copy(), now)
        return df
    except Exception as e:
        logger.error(f"DataProxy Error fetching KIS data for {symbol}: {e}")
        return pd.DataFrame()

yf.download = _proxy_download

# ============================================================
# PART 2: yf.Ticker() Shim (신규 — 15+ 모듈 수정 없이 동작)
# ============================================================

class KISTickerProxy:
    """
    yf.Ticker() 대체 프록시 클래스.
    
    KIS API에서 제공하는 데이터로 최선의 결과를 반환하고,
    지원하지 않는 기능(옵션, 인사이더 등)은 빈 데이터로 안전하게 반환.
    
    지원 메서드:
    - .info → 현재가 + 가격 기반 메트릭
    - .history() → kis_data.download()
    - .options → 빈 리스트
    - .option_chain() → 빈 DataFrame
    - .institutional_holders → 빈 DataFrame
    - .insider_transactions → 빈 DataFrame
    - .earnings_history → 빈 DataFrame
    - .calendar → 빈 DataFrame
    """
    
    def __init__(self, symbol: str):
        self._symbol = symbol
        self._info_cache = None
        self._hist_cache = {}
    
    @property
    def info(self) -> dict:
        """주식 기본 정보 — KIS API 현재가로 구성"""
        if self._info_cache is not None:
            return self._info_cache
        
        try:
            import kis_data
            price_data = kis_data.get_current_price(self._symbol)
            # Use 1mo history instead of 1y for drastically faster screening
            # Most filters only need recent volume and price trend
            df = kis_data.download(self._symbol, period="1mo", progress=False)
            
            info = {
                'symbol': self._symbol,
                'regularMarketPrice': 0,
                'previousClose': 0,
                'averageVolume': 0,
                'volume': 0,
                'marketCap': 0,
                'shortPercentOfFloat': 0,
                'institutionPercentHeld': 0,
                'insidersPercentHeld': 0,
                'earningsGrowth': 0,
                'revenueGrowth': 0,
                'trailingPE': 0,
                'forwardPE': 0,
                'beta': 1.0,
                'fiftyTwoWeekHigh': 0,
                'fiftyTwoWeekLow': 0,
            }
            
            if price_data:
                info['regularMarketPrice'] = price_data.get('last', 0)
                info['previousClose'] = price_data.get('base', 0)
                info['volume'] = price_data.get('tvol', 0)
            
            if df is not None and not df.empty:
                close = df['Close']
                info['averageVolume'] = int(df['Volume'].mean())
                info['fiftyTwoWeekHigh'] = float(close.max())
                info['fiftyTwoWeekLow'] = float(close.min())
                info['marketCap'] = float(close.iloc[-1]) * info['averageVolume'] * 20
                
                # Growth proxies from price
                if len(df) >= 60:
                    info['earningsGrowth'] = float(close.iloc[-1] / close.iloc[0] - 1)
                    info['revenueGrowth'] = info['earningsGrowth'] * 0.6
                
                # Beta proxy (volatility relative to 1.0 default)
                returns = close.pct_change().dropna()
                if len(returns) > 20:
                    info['beta'] = float(returns.std() * (252 ** 0.5) / 0.16)  # vs ~16% SPY annual vol
                
                # Institutional ownership proxy from price stability
                vol = float(returns.std())
                if vol < 0.015:
                    info['institutionPercentHeld'] = 0.70
                elif vol < 0.025:
                    info['institutionPercentHeld'] = 0.50
                elif vol < 0.04:
                    info['institutionPercentHeld'] = 0.30
                else:
                    info['institutionPercentHeld'] = 0.15
            
            self._info_cache = info
            return info
            
        except Exception as e:

            logger.debug(f"KISTickerProxy.info failed for {self._symbol}: {e}")
            return {'symbol': self._symbol}
    
    def history(self, period: str = "1mo", interval: str = "1d", **kwargs) -> pd.DataFrame:
        """주가 히스토리 — kis_data.download()로 라우팅"""
        cache_key = f"{period}_{interval}"
        if cache_key in self._hist_cache:
            return self._hist_cache[cache_key].copy()
        
        try:
            df = _proxy_download(self._symbol, period=period, interval=interval, progress=False)
            if df is not None and not df.empty:
                self._hist_cache[cache_key] = df.copy()
                return df
        except Exception as e:
            logger.debug(f"KISTickerProxy.history failed for {self._symbol}: {e}")
        
        return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])
    
    @property
    def options(self) -> list:
        """옵션 만기일 — KIS API 미지원, 빈 리스트 반환"""
        return []
    
    def option_chain(self, date: str = None):
        """옵션 체인 — KIS API 미지원, 빈 결과 반환"""
        class EmptyChain:
            calls = pd.DataFrame(columns=['strike', 'volume', 'openInterest', 'impliedVolatility'])
            puts = pd.DataFrame(columns=['strike', 'volume', 'openInterest', 'impliedVolatility'])
        return EmptyChain()
    
    @property
    def institutional_holders(self) -> pd.DataFrame:
        """기관 보유 현황 — KIS API 미지원"""
        return pd.DataFrame(columns=['Holder', 'Shares', 'Date Reported', '% Out', 'Value'])
    
    @property
    def insider_transactions(self) -> pd.DataFrame:
        """내부자 거래 — KIS API 미지원"""
        return pd.DataFrame(columns=['Shares', 'Value', 'Start Date', 'Text'])
    
    @property
    def earnings_history(self) -> pd.DataFrame:
        """실적 히스토리 — KIS API 미지원"""
        return pd.DataFrame(columns=['epsActual', 'epsEstimate', 'epsDifference', 'surprisePercent'])
    
    @property
    def calendar(self) -> pd.DataFrame:
        """실적 달력 — KIS API 미지원"""
        return pd.DataFrame()
    
    @property
    def recommendations(self) -> pd.DataFrame:
        """애널리스트 추천 — KIS API 미지원"""
        return pd.DataFrame(columns=['Firm', 'To Grade', 'From Grade', 'Action'])
    
    @property
    def major_holders(self) -> pd.DataFrame:
        """주요 주주 — KIS API 미지원"""
        return pd.DataFrame()
    
    @property  
    def dividends(self) -> pd.Series:
        """배당금 — KIS API 미지원"""
        return pd.Series(dtype=float)
    
    @property
    def splits(self) -> pd.Series:
        """주식 분할 — KIS API 미지원"""
        return pd.Series(dtype=float)


# Save original and apply monkey patch
# NOTE: Must save as attribute on yf module so kis_data.py can access via
# hasattr(yf, '_original_yf_Ticker'). Local var alone is NOT accessible there.
_original_yf_Ticker = yf.Ticker
yf._original_yf_Ticker = yf.Ticker   # <-- this is what kis_data.py checks
yf.Ticker = KISTickerProxy

logger.info("Data Proxy initialized: yfinance.download AND yfinance.Ticker have been shimmed to kis_data.")
