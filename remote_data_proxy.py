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

def _proxy_download(tickers, *args, **kwargs):
    """
    Intercepts yfinance download requests and routes them to kis_data.download.
    """
    period = kwargs.get('period', '3mo')
    interval = kwargs.get('interval', '1d')
    progress = kwargs.get('progress', False)
    auto_adjust = kwargs.get('auto_adjust', True)
    
    BYPASS_TICKERS = [
        "KRW=X", "TIP", "HYG", "TLT", "XLI", "XLF", 
        "VIXY", "UUP", "LQD", "GLD", "SPY", 
        "XLK", "XLV", "XLC", "XLY", "XLP", "XLE", "XLU", "XLRE", "XLB"
    ]
    
    if isinstance(tickers, list) and len(tickers) == 1:
        symbol = tickers[0]
    elif isinstance(tickers, str):
        symbol = tickers
    else:
        logger.warning(f"DataProxy: Multiple tickers unsupported by KIS direct proxy. Passing to original yf. {tickers}")
        return _original_yf_download(tickers, *args, **kwargs)

    # Bypass KIS for specific macro/FX tickers
    if any(bt in symbol.upper() for bt in BYPASS_TICKERS):
        logger.debug(f"DataProxy: Bypassing KIS for macro ticker {symbol}")
        df = _original_yf_download(tickers, *args, **kwargs)
        if df is not None and not df.empty:
            return df
            
        # --- yfinance download FAILED -> Attempt recovery for macro tickers ---
        symbol_upper = symbol.upper()
        logger.warning(f"yfinance download failed for macro {symbol_upper} on remote. Attempting multi-source fallback recovery...")
        
        recovered_df = pd.DataFrame()
        days_back = 90
        if period == '1mo':
            days_back = 30
        elif period == '3mo':
            days_back = 90
        elif period == '6mo':
            days_back = 180
        elif period == '1y':
            days_back = 365
            
        try:
            # 1. KIS API Fallback (for standard ETFs like SPY, GLD, TLT)
            if not symbol_upper.startswith("^") and symbol_upper not in ["BTC-USD", "KRW=X", "CL=F"]:
                logger.info(f"Attempting KIS API fallback download for {symbol_upper} on remote...")
                df = kis_download(tickers=symbol_upper, period=period, interval=interval, 
                                  progress=progress, auto_adjust=auto_adjust)
                if df is not None and not df.empty:
                    recovered_df = df

            # 2. Multi-source Fallbacks (Finnhub & FRED)
            if recovered_df.empty:
                # 2.1. Crypto Fallback
                if symbol_upper == "BTC-USD":
                    from finnhub_client import get_finnhub_client
                    fc = get_finnhub_client()
                    if fc.is_enabled():
                        res = fc.get_candles("BINANCE:BTCUSDT", category="crypto", days_back=days_back)
                        recovered_df = _parse_finnhub_candle(res)
                    if recovered_df.empty:
                        from fred_macro import get_fred_analyzer
                        fa = get_fred_analyzer()
                        if fa.is_enabled():
                            recovered_df = fa.fetch_series_df("CBBTCUSD", limit=days_back * 2)
                            
                # 2.2. Oil Fallback (via USO ETF or FRED WTI Spot Price)
                elif symbol_upper == "CL=F":
                    from finnhub_client import get_finnhub_client
                    fc = get_finnhub_client()
                    if fc.is_enabled():
                        res = fc.get_candles("USO", category="stock", days_back=days_back)
                        recovered_df = _parse_finnhub_candle(res)
                    if recovered_df.empty:
                        from fred_macro import get_fred_analyzer
                        fa = get_fred_analyzer()
                        if fa.is_enabled():
                            recovered_df = fa.fetch_series_df("DCOILWTICO", limit=days_back * 2)
                            
                # 2.3. Forex Fallback (Finnhub USD_KRW or FRED DEXKOUS)
                elif symbol_upper == "KRW=X":
                    from finnhub_client import get_finnhub_client
                    fc = get_finnhub_client()
                    if fc.is_enabled():
                        res = fc.get_candles("OANDA:USD_KRW", category="forex", days_back=days_back)
                        recovered_df = _parse_finnhub_candle(res)
                    if recovered_df.empty:
                        from fred_macro import get_fred_analyzer
                        fa = get_fred_analyzer()
                        if fa.is_enabled():
                            recovered_df = fa.fetch_series_df("DEXKOUS", limit=days_back * 2)
                            
                # 2.4. VIX Fallback (FRED VIXCLS)
                elif symbol_upper in ["^VIX", "VIXY"]:
                    from fred_macro import get_fred_analyzer
                    fa = get_fred_analyzer()
                    if fa.is_enabled():
                        recovered_df = fa.get_vix_history(days_back=days_back)
                        
                # 2.5. Standard Macro ETFs
                elif any(etf in symbol_upper for etf in ["SPY", "TLT", "GLD", "TIP", "HYG", "UUP", "LQD", "XLI", "XLF", "XLK", "XLV", "XLC", "XLY", "XLP", "XLE", "XLU", "XLRE", "XLB"]):
                    from finnhub_client import get_finnhub_client
                    fc = get_finnhub_client()
                    if fc.is_enabled():
                        res = fc.get_candles(symbol_upper, category="stock", days_back=days_back)
                        recovered_df = _parse_finnhub_candle(res)
        except Exception as recovery_err:
            logger.error(f"Failed to recover {symbol_upper} via fallback sources on remote: {recovery_err}")
            
        if recovered_df is not None and not recovered_df.empty:
            logger.info(f"SUCCESSFULLY recovered {symbol_upper} macro DataFrame from backup sources on remote (len={len(recovered_df)})")
            return recovered_df
            
        return pd.DataFrame()

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

def _parse_finnhub_candle(res: dict) -> pd.DataFrame:
    if not res or res.get("s") != "ok":
        return pd.DataFrame()
    try:
        df = pd.DataFrame({
            'Open': res['o'],
            'High': res['h'],
            'Low': res['l'],
            'Close': res['c'],
            'Volume': res['v']
        })
        df.index = pd.to_datetime(res['t'], unit='s')
        df.index.name = 'Date'
        df['Adj Close'] = df['Close']
        for col in df.columns:
            df[col] = df[col].astype('float64')
        return df.sort_index()
    except Exception as e:
        logger.error(f"Error parsing Finnhub candle JSON to DataFrame: {e}")
        return pd.DataFrame()

yf.download = _proxy_download

# ============================================================
# PART 2: yf.Ticker() Shim (신규 — 15+ 모듈 수정 없이 동작)
# ============================================================

import os
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FUNDAMENTAL_CACHE_FILE = os.path.join(_CURRENT_DIR, "fundamental_cache.json")

def _load_fundamental_cache() -> dict:
    import json, os
    try:
        if os.path.exists(FUNDAMENTAL_CACHE_FILE):
            with open(FUNDAMENTAL_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.debug(f"Failed to load fundamental cache: {e}")
    return {}

def _save_fundamental_cache(cache: dict):
    import json
    try:
        with open(FUNDAMENTAL_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.debug(f"Failed to save fundamental cache: {e}")


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
        """주식 기본 정보 — yfinance, Finnhub, KIS API 및 캐시를 결합한 4단계 Fallback"""
        if self._info_cache is not None:
            return self._info_cache
            
        symbol = self._symbol.upper()
        now = time.time()
        
        # 1. 파일 캐시 체크
        file_cache = _load_fundamental_cache()
        if symbol in file_cache:
            entry = file_cache[symbol]
            if now - entry.get("timestamp", 0) < 86400:
                self._info_cache = entry.get("data")
                return self._info_cache

        info = {
            'symbol': symbol,
            'regularMarketPrice': 0.0,
            'previousClose': 0.0,
            'averageVolume': 0.0,
            'volume': 0.0,
            'marketCap': 0.0,
            'shortPercentOfFloat': 0.0,
            'institutionPercentHeld': 0.0,
            'insidersPercentHeld': 0.0,
            'earningsGrowth': 0.0,
            'revenueGrowth': 0.0,
            'trailingPE': 0.0,
            'forwardPE': 0.0,
            'pegRatio': 0.0,
            'priceToBook': 0.0,
            'priceToSalesTrailing12Months': 0.0,
            'trailingEps': 0.0,
            'profitMargins': 0.0,
            'returnOnEquity': 0.0,
            'debtToEquity': 0.0,
            'currentRatio': 0.0,
            'freeCashflow': 0.0,
            'beta': 1.0,
            'fiftyTwoWeekHigh': 0.0,
            'fiftyTwoWeekLow': 0.0,
            'sector': '',
        }
        
        resolved_layer = "default"
        
        # Layer 1: Live original yfinance
        try:
            orig_ticker_cls = getattr(yf, "_original_yf_Ticker", None) or getattr(yf, "_OriginalTicker", None)
            if orig_ticker_cls:
                orig_ticker = orig_ticker_cls(symbol)
                orig_info = orig_ticker.info
                if orig_info and isinstance(orig_info, dict) and orig_info.get("trailingPE", 0) > 0:
                    for k, v in orig_info.items():
                        if k in info:
                            info[k] = v
                    info['sector'] = orig_info.get('sector', '')
                    resolved_layer = "yfinance"
        except Exception as e:
            logger.debug(f"Layer 1 (yfinance) failed for {symbol}: {e}")

        # Layer 2: Finnhub API Backup
        if resolved_layer == "default":
            try:
                from finnhub_client import get_finnhub_client
                fc = get_finnhub_client()
                if fc.is_enabled():
                    metrics_data = fc.get_basic_financials(symbol)
                    profile_data = fc.get_company_profile(symbol)
                    
                    if metrics_data and "metric" in metrics_data:
                        m = metrics_data["metric"]
                        
                        info['trailingPE'] = float(m.get("peTTM") or m.get("peBasicExclExtraTTM") or 0.0)
                        info['forwardPE'] = float(m.get("forwardPE") or 0.0)
                        info['pegRatio'] = float(m.get("pegTTM") or m.get("forwardPEG") or 0.0)
                        info['priceToBook'] = float(m.get("pb") or m.get("pbQuarterly") or m.get("pbAnnual") or 0.0)
                        info['priceToSalesTrailing12Months'] = float(m.get("psTTM") or m.get("psAnnual") or 0.0)
                        info['trailingEps'] = float(m.get("epsTTM") or m.get("epsBasicExclExtraItemsTTM") or 0.0)
                        
                        info['earningsGrowth'] = float(m.get("epsGrowthTTMYoy") or m.get("epsGrowthQuarterlyYoy") or 0.0) / 100.0
                        info['revenueGrowth'] = float(m.get("revenueGrowthTTMYoy") or m.get("revenueGrowthQuarterlyYoy") or 0.0) / 100.0
                        info['profitMargins'] = float(m.get("netProfitMarginTTM") or m.get("netProfitMarginAnnual") or 0.0) / 100.0
                        info['returnOnEquity'] = float(m.get("roeTTM") or m.get("roeRfy") or 0.0) / 100.0
                        
                        info['debtToEquity'] = float(m.get("totalDebt/totalEquityQuarterly") or m.get("totalDebt/totalEquityAnnual") or 0.0) * 100.0
                        info['currentRatio'] = float(m.get("currentRatioQuarterly") or m.get("currentRatioAnnual") or 0.0)
                        
                        info['fiftyTwoWeekHigh'] = float(m.get("52WeekHigh") or 0.0)
                        info['fiftyTwoWeekLow'] = float(m.get("52WeekLow") or 0.0)
                        info['marketCap'] = float(m.get("marketCapitalization") or 0.0) * 1000000.0
                        info['beta'] = float(m.get("beta") or 1.0)
                        
                        if profile_data:
                            info['sector'] = profile_data.get("finnhubIndustry", "")
                        
                        resolved_layer = "finnhub"
            except Exception as e:
                logger.debug(f"Layer 2 (Finnhub) failed for {symbol}: {e}")

        # Layer 3: KIS API price-detail Backup
        if resolved_layer == "default":
            try:
                import kis_data
                k_data = kis_data.get_fundamental_data(symbol)
                if k_data:
                    info['trailingPE'] = k_data.get("trailingPE", 0.0)
                    info['priceToBook'] = k_data.get("priceToBook", 0.0)
                    info['trailingEps'] = k_data.get("trailingEps", 0.0)
                    info['marketCap'] = k_data.get("marketCap", 0.0)
                    info['fiftyTwoWeekHigh'] = k_data.get("fiftyTwoWeekHigh", 0.0)
                    info['fiftyTwoWeekLow'] = k_data.get("fiftyTwoWeekLow", 0.0)
                    
                    pe = info['trailingPE']
                    pb = info['priceToBook']
                    if pe > 0 and pb > 0:
                        info['returnOnEquity'] = pb / pe
                        
                    resolved_layer = "kis_detail"
            except Exception as e:
                logger.debug(f"Layer 3 (KIS detail) failed for {symbol}: {e}")

        # Layer 4: KIS Current Price (Supplement details anyway)
        try:
            import kis_data
            price_data = kis_data.get_current_price(symbol)
            if price_data:
                info['regularMarketPrice'] = price_data.get('last', 0.0)
                info['previousClose'] = price_data.get('base', 0.0)
                info['volume'] = price_data.get('tvol', 0.0)
                
            df = kis_data.download(symbol, period="1mo", progress=False)
            if df is not None and not df.empty:
                close = df['Close']
                info['averageVolume'] = float(df['Volume'].mean())
                if info['fiftyTwoWeekHigh'] <= 0:
                    info['fiftyTwoWeekHigh'] = float(close.max())
                if info['fiftyTwoWeekLow'] <= 0:
                    info['fiftyTwoWeekLow'] = float(close.min())
                if info['marketCap'] <= 0:
                    info['marketCap'] = float(close.iloc[-1]) * info['averageVolume'] * 20
                if info['earningsGrowth'] <= 0 and len(df) >= 20:
                    info['earningsGrowth'] = float(close.iloc[-1] / close.iloc[0] - 1)
                    info['revenueGrowth'] = info['earningsGrowth'] * 0.6
                
                returns = close.pct_change().dropna()
                if len(returns) > 15:
                    info['beta'] = float(returns.std() * (252 ** 0.5) / 0.16)
        except Exception as e:
            logger.debug(f"Layer 4 (KIS Price supplement) failed for {symbol}: {e}")

        logger.info(f"Fundamental data resolved for {symbol} via Layer: [{resolved_layer}] (PE={info['trailingPE']:.2f}, PB={info['priceToBook']:.2f}, ROE={info['returnOnEquity']*100:.1f}%)")

        # 캐시 쓰기
        self._info_cache = info
        file_cache[symbol] = {
            "timestamp": now,
            "data": info
        }
        _save_fundamental_cache(file_cache)
        
        return info
    
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
