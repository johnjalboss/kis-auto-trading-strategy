"""
KIS Data Provider
==================
한국투자증권 API를 통한 해외주식 데이터 조회 모듈.
yfinance를 완전 대체하여 모든 시세/차트 데이터를 KIS API로 조달.

핵심 기능:
1. get_current_price()  — 현재가 (TR: HHDFS00000300)
2. get_daily_ohlcv()    — 일봉 OHLCV (TR: HHDFS76240000)
3. get_volume_rank()    — 거래량순위 (TR: HHDFS76410000)
4. download()           — yf.download() 호환 drop-in 대체
"""

import time
import threading
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Union
from loguru import logger

import config
from auth import get_auth, AutoAuth


# ==============================================
# Exchange Mapping
# ==============================================

# yfinance ticker → KIS exchange code mapping
TICKER_EXCHANGE_MAP = {
    # Major indices (지수) — yfinance uses ^ prefix
    "^VIX": ("SHS", "VIX"),     # VIX는 KIS에서 직접 안 됨 → fallback 필요
    "^GSPC": ("SHS", "SPX"),
    "^DJI": ("SHS", "DJI"),
    "^IXIC": ("SHS", "COMP"),
    "^TNX": ("SHS", "TNX"),     # 10Y yield — KIS 미지원
    "^IRX": ("SHS", "IRX"),     # 13W T-bill — KIS 미지원
}

# Default US exchange detection
US_EXCHANGES = {
    "NAS": "나스닥",
    "NYS": "뉴욕",
    "AMS": "아멕스",
}

# Persistent cache of symbols that failed all KIS exchanges (e.g. unlisted OTCs)
# These will skip API calls immediately to prevent 5-minute timeout lags
_BLACKLIST_PATH = Path("kis_symbol_blacklist.json")
_KIS_UNSUPPORTED: set = set()

def _load_blacklist():
    global _KIS_UNSUPPORTED
    if _BLACKLIST_PATH.exists():
        try:
            data = json.loads(_BLACKLIST_PATH.read_text(encoding="utf-8"))
            _KIS_UNSUPPORTED = set(s.upper() for s in data.get("symbols", []))
        except Exception:
            pass

def _save_blacklist_symbol(sym: str):
    global _KIS_UNSUPPORTED
    _KIS_UNSUPPORTED.add(sym.upper())
    try:
        data = {"symbols": sorted(list(_KIS_UNSUPPORTED))}
        _BLACKLIST_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass

_load_blacklist()

# Rate limiter — KIS API는 초당 ~2건
_last_call_time = 0.0
_MIN_INTERVAL = 0.55  # seconds between calls
_rate_limit_lock = threading.Lock()


def _rate_limit():
    """KIS API 초당 호출 제한 준수 (Thread-Safe)"""
    global _last_call_time
    with _rate_limit_lock:
        now = time.time()
        elapsed = now - _last_call_time
        if elapsed < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - elapsed)
        _last_call_time = time.time()


def _detect_exchange(symbol: str) -> str:
    """종목 코드에서 거래소 추정 (미국 한정)
    
    일반적으로 NAS가 가장 많고, 실패 시 NYS → AMS 순으로 시도.
    실제로는 대부분 NAS 또는 NYS.
    """
    # 미국 이외 거래소 처리 (향후 확장)
    return "NAS"  # Default: NASDAQ — 오류 시 NYS fallback


def _guess_exchange_for_symbol(symbol: str) -> str:
    """Try to determine the exchange for a US stock symbol.
    Uses cached results and falls back to attempting API calls."""
    
    # Known ETFs/stocks on specific exchanges
    NYSE_KNOWN = {
        'SPY', 'QQQ', 'DIA', 'IWM', 'XLF', 'XLE', 'XLK', 'XLV', 'XLI',
        'XLU', 'XLP', 'XLY', 'XLB', 'XLRE', 'GLD', 'SLV', 'USO', 'UNG',
        'TLT', 'IEF', 'HYG', 'LQD', 'JNK', 'BA', 'CAT', 'GE', 'MMM',
        'JPM', 'GS', 'MS', 'WFC', 'BAC', 'C', 'V', 'MA', 'DIS', 'HD',
        'WMT', 'KO', 'PEP', 'PG', 'JNJ', 'UNH', 'CVX', 'XOM', 'CRM',
        'BABA', 'IBM', 'T', 'VZ', 'PFE', 'MRK', 'ABT', 'TMO', 'DHR',
        'PM', 'NEE', 'UBER', 'PLTR', 'XYZ', 'SNAP', 'DKNG', 'NIO',
    }
    AMEX_KNOWN = {'AMC', 'SNDL', 'CLOV', 'WKHS', 'PHUN'}
    
    if symbol.upper() in NYSE_KNOWN:
        return "NYS"
    if symbol.upper() in AMEX_KNOWN:
        return "AMS"
    return "NAS"


# ==============================================
# Core API Functions
# ==============================================

def get_fundamental_data(symbol: str, exchange: str = None) -> Optional[Dict]:
    """해외주식 시세 상세 조회 (TR: HHDFS76200200) - PER, PBR, EPS, BPS, 시총 등 조회
    
    Args:
        symbol: 종목코드 (예: AAPL, TSLA)
        exchange: 거래소코드 (NAS/NYS/AMS). None이면 자동 감지
        
    Returns:
        dict containing fundamental metrics or None on error
    """
    if exchange is None:
        exchange = _guess_exchange_for_symbol(symbol)
        
    auth = get_auth()
    
    exchanges_to_try = [exchange]
    for ex in ["NAS", "NYS", "AMS"]:
        if ex not in exchanges_to_try:
            exchanges_to_try.append(ex)
            
    for excd in exchanges_to_try:
        _rate_limit()
        
        headers = auth.get_headers(tr_id="HHDFS76200200")
        params = {
            "AUTH": "",
            "EXCD": excd,
            "SYMB": symbol.upper()
        }
        
        try:
            resp = requests.get(
                f"{config.BASE_URL}/uapi/overseas-price/v1/quotations/price-detail",
                headers=headers,
                params=params,
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("rt_cd") == "0" and data.get("output"):
                o = data["output"]
                return {
                    "symbol": symbol.upper(),
                    "exchange": excd,
                    "last": float(o.get("last", 0) or 0),
                    "base": float(o.get("base", 0) or 0),
                    "open": float(o.get("open", 0) or 0),
                    "high": float(o.get("high", 0) or 0),
                    "low": float(o.get("low", 0) or 0),
                    "fiftyTwoWeekHigh": float(o.get("h52p", 0) or 0),
                    "fiftyTwoWeekHighDate": o.get("h52d", ""),
                    "fiftyTwoWeekLow": float(o.get("l52p", 0) or 0),
                    "fiftyTwoWeekLowDate": o.get("l52d", ""),
                    "trailingPE": float(o.get("perx", 0) or 0),
                    "priceToBook": float(o.get("pbrx", 0) or 0),
                    "trailingEps": float(o.get("epsx", 0) or 0),
                    "bookValue": float(o.get("bpsx", 0) or 0),
                    "sharesOutstanding": int(o.get("shar", 0) or 0),
                    "marketCap": float(o.get("tomv", 0) or 0)
                }
        except Exception as e:
            logger.debug(f"KIS price-detail failed for {symbol} on {excd}: {e}")
            continue
            
    return None


def get_current_price(symbol: str, exchange: str = None) -> Optional[Dict]:
    """해외주식 현재체결가 조회 (TR: HHDFS00000300)
    
    Args:
        symbol: 종목코드 (예: AAPL, TSLA)
        exchange: 거래소코드 (NAS/NYS/AMS). None이면 자동 감지
    
    Returns:
        dict with keys: last, open, high, low, base(전일종가), 
                       tvol(거래량), pvol(전일거래량), diff, rate, etc.
        None on error
    """
    if exchange is None:
        exchange = _guess_exchange_for_symbol(symbol)
    
    auth = get_auth()
    
    # Try primary exchange, fallback to others if not found
    exchanges_to_try = [exchange]
    for ex in ["NAS", "NYS", "AMS"]:
        if ex not in exchanges_to_try:
            exchanges_to_try.append(ex)
    
    for excd in exchanges_to_try:
        _rate_limit()
        
        headers = auth.get_headers(tr_id="HHDFS00000300")
        params = {
            "EXCD": excd,
            "SYMB": symbol.upper(),
        }
        
        try:
            resp = requests.get(
                f"{config.BASE_URL}/uapi/overseas-price/v1/quotations/price",
                headers=headers,
                params=params,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("rt_cd") == "0" and data.get("output"):
                output = data["output"]
                # 유효한 데이터인지 확인 (last가 0이면 해당 거래소에 없음)
                last_price = output.get("last", "0")
                if last_price and float(last_price) > 0:
                    return {
                        "symbol": symbol,
                        "exchange": excd,
                        "last": float(output.get("last", 0)),
                        "open": float(output.get("open", 0)),
                        "high": float(output.get("high", 0)),
                        "low": float(output.get("low", 0)),
                        "base": float(output.get("base", 0)),  # 전일종가
                        "tvol": int(output.get("tvol", 0)),     # 거래량
                        "pvol": int(output.get("pvol", 0)),     # 전일거래량
                        "diff": float(output.get("diff", 0)),   # 전일대비
                        "rate": float(output.get("rate", 0)),   # 등락율
                        "ordy": output.get("ordy", ""),         # 매수가능여부  
                        "t_xprc": float(output.get("t_xprc", 0)),  # 시간외 현재가
                        "t_rate": float(output.get("t_rate", 0)),   # 시간외 등락률
                    }
            # If rt_cd != 0 or last is 0, try next exchange
        except Exception as e:
            logger.debug("Price fetch error for {}@{}: {}", symbol, excd, e)
            continue
    
    logger.warning("Could not fetch price for {} on any exchange", symbol)
    return None


def _cleanse_ohlcv_data(df: pd.DataFrame) -> pd.DataFrame:
    """[QUANT DATA INTEGRITY] 데이터 무결성 검증 및 이상치 클렌징 엔진
    
    1. NaN 및 0 이하 가격 처리 (전진/후진 채우기)
    2. 이상치 불량 틱 (Bad-Tick: 3-Sigma 초과 스파이크) 보정
    3. 거래량 0 무효 데이터 보정
    """
    if df is None or df.empty:
        return df
    
    df = df.copy()
    
    # 1. NaN 및 비정상 가격 보정
    cols = ['Open', 'High', 'Low', 'Close']
    for c in cols:
        if c in df.columns:
            df[c] = df[c].replace(0, np.nan)
            df[c] = df[c].ffill().bfill()
            
    if 'Volume' in df.columns:
        df['Volume'] = df['Volume'].fillna(0).apply(lambda x: max(0, x))
        
    # 2. 불량 틱 (Spurious Bad-Tick) 3-Sigma 이상치 보정
    if len(df) >= 20 and 'Close' in df.columns:
        returns = df['Close'].pct_change()
        mean_ret = returns.mean()
        std_ret = returns.std()
        
        if std_ret > 0:
            # 3.5 표준편차 초과 일시적 스파이크 감지 및 억제
            outliers = (returns - mean_ret).abs() > (3.5 * std_ret)
            for idx in df.index[outliers]:
                # 연속 데이터인 경우 이전 종가 기준으로 스파이크 캡 적용
                prev_idx = df.index.get_loc(idx) - 1
                if prev_idx >= 0:
                    prev_close = df['Close'].iloc[prev_idx]
                    capped_close = prev_close * (1 + np.clip(returns.loc[idx], -0.20, 0.20))
                    df.loc[idx, 'Close'] = capped_close
                    if 'High' in df.columns: df.loc[idx, 'High'] = max(df.loc[idx, 'High'], capped_close)
                    if 'Low' in df.columns: df.loc[idx, 'Low'] = min(df.loc[idx, 'Low'], capped_close)
                    
    return df


def get_daily_ohlcv(symbol: str, exchange: str = None, 
                     days: int = 100, period_type: str = "0",
                     adjusted: bool = True) -> Optional[pd.DataFrame]:
    """해외주식 기간별시세 조회 (TR: HHDFS76240000)
    
    Args:
        symbol: 종목코드 (예: AAPL)
        exchange: 거래소코드 (NAS/NYS/AMS)
        days: 조회할 일수 (최대 100건/호출)
        period_type: "0"=일, "1"=주, "2"=월
        adjusted: 수정주가 반영 여부
    
    Returns:
        pd.DataFrame with columns: Open, High, Low, Close, Volume
        Index: DatetimeIndex
        None on error
    """
    if exchange is None:
        exchange = _guess_exchange_for_symbol(symbol)
    
    # Skip known-unsupported symbols immediately (session-level cache)
    if symbol.upper() in _KIS_UNSUPPORTED:
        pass  # Fall through to yfinance
    else:
        auth = get_auth()
        
        # Try primary exchange, fallback
        exchanges_to_try = [exchange]
        for ex in ["NAS", "NYS", "AMS"]:
            if ex not in exchanges_to_try:
                exchanges_to_try.append(ex)
        
        for excd in exchanges_to_try:
            _rate_limit()
            
            headers = auth.get_headers(tr_id="HHDFS76240000")
            params = {
                "EXCD": excd,
                "SYMB": symbol.upper(),
                "GUBN": period_type,
                "BYMD": "",  # 공란 = 오늘 기준
                "MODP": "1" if adjusted else "0",
            }
            
            try:
                resp = requests.get(
                    f"{config.BASE_URL}/uapi/overseas-price/v1/quotations/dailyprice",
                    headers=headers,
                    params=params,
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                
                if data.get("rt_cd") == "0" and data.get("output2"):
                    records = data["output2"]
                    
                    if not records:
                        continue
                    
                    rows = []
                    for r in records:
                        xymd = r.get("xymd", "")
                        if not xymd or xymd == "0":
                            continue
                        try:
                            rows.append({
                                "Date": pd.Timestamp(xymd),
                                "Open": float(r.get("open", 0)),
                                "High": float(r.get("high", 0)),
                                "Low": float(r.get("low", 0)),
                                "Close": float(r.get("clos", 0)),
                                "Volume": int(r.get("tvol", 0)),
                            })
                        except (ValueError, TypeError):
                            continue
                    
                    if not rows:
                        continue
                    
                    df = pd.DataFrame(rows)
                    df.set_index("Date", inplace=True)
                    df.sort_index(inplace=True)
                    
                    # 필요한 일수만큼 자르기
                    if len(df) > days:
                        df = df.tail(days)
                    
                    if len(df) >= 2:
                        return df
                        
            except Exception as e:
                logger.debug("OHLCV fetch error for {}@{}: {}", symbol, excd, e)
                continue
        
        # All KIS exchanges failed — cache and persist this symbol to skip next time
        _save_blacklist_symbol(symbol.upper())
    
    import os
    macro_whitelist = {"^VIX", "^GSPC", "^DJI", "^IXIC", "^TNX", "^IRX", "BTC-USD", "CL=F", "UUP", "GLD", "TLT", "SPY", "QQQ", "DIA", "IWM", "BRK-B", "BRKB"}
    if os.getenv("DISABLE_YFINANCE_FALLBACK", "true").lower() == "true" and symbol.upper() not in macro_whitelist:
        return None

    logger.warning("Could not fetch daily OHLCV for {} via KIS API, falling back to yfinance", symbol)

    # KIS 심볼 → yfinance 심볼 변환 (e.g. BRKB → BRK-B)
    YF_SYMBOL_MAP = {"BRKB": "BRK-B", "BRKB": "BRK-B"}
    yf_symbol = YF_SYMBOL_MAP.get(symbol.upper(), symbol)

    try:
        import yfinance as yf
        # 방어벽: data_proxy에 의해 yf.Ticker가 KISTickerProxy로 패치된 경우 원본 사용
        if hasattr(yf, "_original_yf_Ticker"):
            ticker = yf._original_yf_Ticker(yf_symbol)
        else:
            ticker = yf.Ticker(yf_symbol)
        period_str = "max"
        if days <= 5: period_str = "5d"
        elif days <= 20: period_str = "1mo"
        elif days <= 60: period_str = "3mo"
        elif days <= 120: period_str = "6mo"
        elif days <= 250: period_str = "1y"
        elif days <= 500: period_str = "2y"
        elif days <= 1250: period_str = "5y"
        elif days <= 2500: period_str = "10y"

        df = ticker.history(period=period_str, auto_adjust=True)
        if df is not None and not df.empty:
            # [DATA CLEANSER] 이상치 불량 틱(Bad-Tick) 및 NaN 정제
            df = _cleanse_ohlcv_data(df)
            if len(df) > days:
                df = df.tail(days)
            return df
    except Exception as e:
        logger.error("yfinance fallback failed for {} (yf_symbol={}): {}", symbol, yf_symbol, e)

    return None


def get_intraday_ohlcv(symbol: str, exchange: str = None, 
                       interval_mins: str = "15", 
                       max_records: int = 120) -> Optional[pd.DataFrame]:
    """해외주식 분봉조회 (TR: HHDFS76950200)
    
    Args:
        symbol: 종목코드
        exchange: NAS/NYS/AMS
        interval_mins: "1", "5", "10", "15", "30" 등 분 단위 문자열
        max_records: 가져올 최대 캔들 수 (1회 호출당 최대 120건)
        
    Returns:
        pd.DataFrame with Open, High, Low, Close, Volume
        Index is DatetimeIndex (US Local Time for the symbol's market)
    """
    if exchange is None:
        exchange = _guess_exchange_for_symbol(symbol)
        
    auth = get_auth()
    exchanges_to_try = [exchange]
    for ex in ["NAS", "NYS", "AMS"]:
        if ex not in exchanges_to_try:
            exchanges_to_try.append(ex)
            
    for excd in exchanges_to_try:
        _rate_limit()
        
        headers = auth.get_headers(tr_id="HHDFS76950200")
        params = {
            "AUTH": "",
            "EXCD": excd,
            "SYMB": symbol.upper(),
            "NMIN": interval_mins,
            "PINC": "0",  # 0: 전체 시간대, 1: 정규장만 (선택적)
            "NEXT": "",
            "NREC": str(min(120, max_records)),
            "FILL": "",
            "KEYB": "",
        }
        
        try:
            resp = requests.get(
                f"{config.BASE_URL}/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice",
                headers=headers,
                params=params,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("rt_cd") == "0" and data.get("output2"):
                records = data["output2"]
                rows = []
                for r in records:
                    xymd = r.get("xymd", "")
                    xhms = r.get("xhms", "")
                    if not xymd or not xhms:
                        continue
                    try:
                        # Convert YYYYMMDD and HHMMSS to expected timestamp
                        # e.g., '20260225' + '123000' -> '2026-02-25 12:30:00'
                        dt_str = xymd + xhms
                        dt = pd.to_datetime(dt_str, format="%Y%m%d%H%M%S")
                        
                        rows.append({
                            "Date": dt,
                            "Open": float(r.get("open", 0)),
                            "High": float(r.get("high", 0)),
                            "Low": float(r.get("low", 0)),
                            "Close": float(r.get("last", 0)), # 분봉 API에서는 종가가 'last'로 옴
                            "Volume": int(r.get("evol", 0)),  # 체결량
                        })
                    except (ValueError, TypeError):
                        continue
                        
                if not rows:
                    continue
                    
                df = pd.DataFrame(rows)
                df.set_index("Date", inplace=True)
                df.sort_index(inplace=True) # oldest to newest
                
                if len(df) >= 2:
                    return df
        except Exception as e:
            logger.debug("Intraday fetch error for {}@{}: {}", symbol, excd, e)
            continue
            
    logger.warning("Could not fetch intraday OHLCV for {} via KIS API, falling back to yfinance", symbol)
    import os
    macro_whitelist = {"^VIX", "^GSPC", "^DJI", "^IXIC", "^TNX", "^IRX", "BTC-USD", "CL=F", "UUP", "GLD", "TLT", "SPY", "QQQ", "DIA", "IWM", "BRK-B", "BRKB"}
    if os.getenv("DISABLE_YFINANCE_FALLBACK", "true").lower() == "true" and symbol.upper() not in macro_whitelist:
        return None
        
    try:
        import yfinance as yf
        if hasattr(yf, "_original_yf_Ticker"):
            ticker = yf._original_yf_Ticker(symbol)
        else:
            ticker = yf.Ticker(symbol)
        
        # Mapping interval
        yf_interval = "15m"
        if interval_mins == "1": yf_interval = "1m"
        elif interval_mins == "5": yf_interval = "5m"
        elif interval_mins == "10": yf_interval = "5m" # yfinance has no 10m
        elif interval_mins == "30": yf_interval = "30m"
        elif interval_mins == "60": yf_interval = "60m"
        
        # Calculate needed period to satisfy max_records
        # 15m interval * 120 candles = ~1800 mins = ~4.5 trading days
        period = "5d"
        if yf_interval == "1m": period = "1d"
        elif yf_interval == "5m": period = "5d"
        elif yf_interval == "30m": period = "1mo"
        elif yf_interval == "60m": period = "1mo"
            
        df = ticker.history(period=period, interval=yf_interval)
        if df is not None and not df.empty:
            if len(df) > max_records:
                df = df.tail(max_records)
            return df
    except Exception as e:
        logger.error("yfinance fallback failed for {}: {}", symbol, e)
        
    return None


def get_volume_rank(exchange: str = "NAS", 
                     min_price: float = 5.0,
                     top_n: int = 30) -> List[Dict]:
    """해외주식 거래량순위 조회 (TR: HHDFS76410000)
    
    Finviz 스크리너를 대체하여 거래량 상위 종목을 KIS API에서 조회.
    
    Args:
        exchange: NAS/NYS/AMS
        min_price: 최소 가격 필터
        top_n: 반환할 종목 수
    
    Returns:
        List of dicts with symbol, name, price, volume, change, etc.
    """
    auth = get_auth()
    _rate_limit()
    
    headers = auth.get_headers(tr_id="HHDFS76410000")
    
    # 거래소코드 매핑 (거래량순위 API는 다른 코드 사용)
    EXCD_MAP = {"NAS": "NAS", "NYS": "NYS", "AMS": "AMS"}
    excd = EXCD_MAP.get(exchange, "NAS")
    
    params = {
        "EXCD": excd,
        "NMIN": "",          # 분전 데이터 (공란=전체)
        "MKET": "",           # 시장 (공란=전체)
        "OVRS_NMIX_TRAD_MKET_CD": "",
    }
    
    try:
        resp = requests.get(
            f"{config.BASE_URL}/uapi/overseas-price/v1/quotations/inquire-search",
            headers=headers,
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("rt_cd") == "0" and data.get("output2"):
            results = []
            for item in data["output2"][:top_n]:
                try:
                    price = float(item.get("last", 0))
                    if price < min_price:
                        continue
                    results.append({
                        "symbol": item.get("symb", ""),
                        "name": item.get("name", ""),
                        "price": price,
                        "volume": int(item.get("tvol", 0)),
                        "change_pct": float(item.get("rate", 0)),
                        "exchange": exchange,
                    })
                except (ValueError, TypeError):
                    continue
            return results
                
    except Exception as e:
        logger.error("Volume rank fetch error: {}", e)
    
    return []


# ==============================================
# Market Analysis APIs (시세분석)
# ==============================================

def get_orderbook(symbol: str, exchange: str = None) -> Optional[Dict]:
    """해외주식 현재가 호가 조회
    
    Returns bid/ask prices and quantities (10 levels).
    Used for: spread analysis, buy/sell wall detection.
    """
    if exchange is None:
        exchange = _guess_exchange_for_symbol(symbol)
    
    auth = get_auth()
    exchanges_to_try = [exchange]
    for ex in ["NAS", "NYS", "AMS"]:
        if ex not in exchanges_to_try:
            exchanges_to_try.append(ex)
    
    for excd in exchanges_to_try:
        _rate_limit()
        headers = auth.get_headers(tr_id="HHDFS76200200")
        params = {"EXCD": excd, "SYMB": symbol.upper()}
        
        try:
            resp = requests.get(
                f"{config.BASE_URL}/uapi/overseas-price/v1/quotations/inquire-asking-price",
                headers=headers, params=params, timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("rt_cd") == "0" and data.get("output1"):
                o = data["output1"]
                last = float(o.get("last", 0))
                if last <= 0:
                    continue
                
                # Parse bid/ask
                bids = []
                asks = []
                for i in range(1, 11):
                    bp = float(o.get(f"bidp{i}", 0))
                    bq = int(o.get(f"bidq{i}", 0))
                    ap = float(o.get(f"askp{i}", 0))
                    aq = int(o.get(f"askq{i}", 0))
                    if bp > 0: bids.append({"price": bp, "qty": bq})
                    if ap > 0: asks.append({"price": ap, "qty": aq})
                
                best_bid = bids[0]["price"] if bids else last
                best_ask = asks[0]["price"] if asks else last
                spread = (best_ask - best_bid) / last * 100 if last > 0 else 0
                
                total_bid_qty = sum(b["qty"] for b in bids)
                total_ask_qty = sum(a["qty"] for a in asks)
                
                return {
                    "symbol": symbol, "exchange": excd, "last": last,
                    "best_bid": best_bid, "best_ask": best_ask,
                    "spread_pct": round(spread, 4),
                    "total_bid_qty": total_bid_qty,
                    "total_ask_qty": total_ask_qty,
                    "bid_ask_ratio": round(total_bid_qty / max(total_ask_qty, 1), 2),
                    "bids": bids[:5], "asks": asks[:5],
                }
        except Exception as e:
            logger.debug("Orderbook fetch error for {}@{}: {}", symbol, excd, e)
            continue
    return None


def get_price_surge(exchange: str = "NAS", sort: str = "1", 
                    top_n: int = 30) -> List[Dict]:
    """해외주식 가격급등락 조회
    
    Returns stocks with sudden price movements.
    sort: "1"=급등, "2"=급락
    """
    auth = get_auth()
    _rate_limit()
    headers = auth.get_headers(tr_id="HHDFS76950300")
    params = {
        "EXCD": exchange,
        "GUBN": sort,  # 1=상승, 2=하락
        "BYMD": "", "MODP": "0",
    }
    
    try:
        resp = requests.get(
            f"{config.BASE_URL}/uapi/overseas-price/v1/quotations/inquire-price-change",
            headers=headers, params=params, timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("rt_cd") == "0" and data.get("output2"):
            results = []
            for item in data["output2"][:top_n]:
                try:
                    price = float(item.get("last", 0))
                    if price < 1:
                        continue
                    results.append({
                        "symbol": item.get("symb", ""),
                        "name": item.get("name", ""),
                        "price": price,
                        "change_pct": float(item.get("rate", 0)),
                        "volume": int(item.get("tvol", 0)),
                        "exchange": exchange,
                        "source": "price_surge",
                    })
                except (ValueError, TypeError):
                    continue
            return results
    except Exception as e:
        logger.debug("Price surge fetch error: {}", e)
    return []


def get_volume_surge(exchange: str = "NAS", top_n: int = 30) -> List[Dict]:
    """해외주식 거래량급증 조회
    
    Returns stocks with sudden volume increases.
    Used for: detecting institutional activity or news catalysts.
    """
    auth = get_auth()
    _rate_limit()
    headers = auth.get_headers(tr_id="HHDFS76950400")
    params = {"EXCD": exchange, "BYMD": "", "MODP": "0"}
    
    try:
        resp = requests.get(
            f"{config.BASE_URL}/uapi/overseas-price/v1/quotations/inquire-volume-change",
            headers=headers, params=params, timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("rt_cd") == "0" and data.get("output2"):
            results = []
            for item in data["output2"][:top_n]:
                try:
                    price = float(item.get("last", 0))
                    if price < 1:
                        continue
                    results.append({
                        "symbol": item.get("symb", ""),
                        "name": item.get("name", ""),
                        "price": price,
                        "change_pct": float(item.get("rate", 0)),
                        "volume": int(item.get("tvol", 0)),
                        "vol_increase_rate": float(item.get("vol_rate", item.get("vrte", 0))),
                        "exchange": exchange,
                        "source": "volume_surge",
                    })
                except (ValueError, TypeError):
                    continue
            return results
    except Exception as e:
        logger.debug("Volume surge fetch error: {}", e)
    return []


def get_buy_strength_rank(exchange: str = "NAS", top_n: int = 30) -> List[Dict]:
    """해외주식 매수체결강도상위 조회
    
    Returns stocks with highest buy execution strength.
    Used for: detecting smart money inflow.
    """
    auth = get_auth()
    _rate_limit()
    headers = auth.get_headers(tr_id="HHDFS76950500")
    params = {"EXCD": exchange, "BYMD": "", "MODP": "0"}
    
    try:
        resp = requests.get(
            f"{config.BASE_URL}/uapi/overseas-price/v1/quotations/inquire-buy-strength",
            headers=headers, params=params, timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("rt_cd") == "0" and data.get("output2"):
            results = []
            for item in data["output2"][:top_n]:
                try:
                    price = float(item.get("last", 0))
                    if price < 1:
                        continue
                    results.append({
                        "symbol": item.get("symb", ""),
                        "name": item.get("name", ""),
                        "price": price,
                        "change_pct": float(item.get("rate", 0)),
                        "buy_strength": float(item.get("seln_str", item.get("bstp", 0))),
                        "volume": int(item.get("tvol", 0)),
                        "exchange": exchange,
                        "source": "buy_strength",
                    })
                except (ValueError, TypeError):
                    continue
            return results
    except Exception as e:
        logger.debug("Buy strength fetch error: {}", e)
    return []


def get_new_highs_lows(exchange: str = "NAS", sort: str = "1",
                       top_n: int = 100) -> List[Dict]:
    """해외주식 신고/신저가 조회 (정확한 랭킹 API 적용)
    
    sort: "1"=신고가, "2"=신저가
    Used for: breakout detection signals.
    """
    auth = get_auth()
    _rate_limit()
    
    headers = auth.get_headers(tr_id="HHDFS76300000")
    params = {
        "AUTH": "",
        "EXCD": exchange,
        "GUBN": "1" if sort == "1" else "0", # 1:신고가, 0:신저가
        "GUBN2": "0",  # 0: 당일
        "NDAY": "6",   # 6: 52주
        "VOL_RANG": "0", # 0: 전체
        "KEYB": ""
    }
    
    try:
        resp = requests.get(
            f"{config.BASE_URL}/uapi/overseas-stock/v1/ranking/new-highlow",
            headers=headers, params=params, timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("output1"):
            results = []
            for item in data["output1"][:top_n]:
                try:
                    price = float(item.get("last", item.get("prpr", 0)))
                    if price < 1:
                        continue
                    results.append({
                        "symbol": item.get("symb", ""),
                        "name": item.get("name", ""),
                        "price": price,
                        "change_pct": float(item.get("rate", 0)),
                        "volume": int(item.get("tvol", 0)),
                        "exchange": exchange,
                        "source": "new_high" if sort == "1" else "new_low",
                    })
                except (ValueError, TypeError):
                    continue
            return results
    except Exception as e:
        logger.debug("New highs/lows fetch error: {}", e)
    return []


def get_sector_prices(exchange: str = "NAS") -> List[Dict]:
    """해외주식 업종별시세 조회
    
    Returns sector-level price data.
    Used for: sector rotation analysis.
    """
    auth = get_auth()
    _rate_limit()
    headers = auth.get_headers(tr_id="HHDFS76410100")
    params = {"EXCD": exchange}
    
    try:
        resp = requests.get(
            f"{config.BASE_URL}/uapi/overseas-price/v1/quotations/inquire-industry-price",
            headers=headers, params=params, timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("rt_cd") == "0" and data.get("output2"):
            results = []
            for item in data["output2"]:
                try:
                    results.append({
                        "sector_code": item.get("sctr_cd", item.get("upjn_cd", "")),
                        "sector_name": item.get("sctr_nm", item.get("upjn_nm", "")),
                        "change_pct": float(item.get("rate", 0)),
                        "volume": int(item.get("tvol", 0)),
                        "exchange": exchange,
                    })
                except (ValueError, TypeError):
                    continue
            return results
    except Exception as e:
        logger.debug("Sector prices fetch error: {}", e)
    return []


def get_rise_fall_rank(exchange: str = "NAS", sort: str = "1",
                       top_n: int = 30) -> List[Dict]:
    """해외주식 상승율/하락율 순위
    
    sort: "1"=상승률 상위, "2"=하락률 상위
    Used for: momentum ranking.
    """
    auth = get_auth()
    _rate_limit()
    headers = auth.get_headers(tr_id="HHDFS76950700")
    params = {
        "EXCD": exchange,
        "GUBN": sort,
        "BYMD": "", "MODP": "0",
    }
    
    try:
        resp = requests.get(
            f"{config.BASE_URL}/uapi/overseas-price/v1/quotations/inquire-rise-fall-rate",
            headers=headers, params=params, timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("rt_cd") == "0" and data.get("output2"):
            results = []
            for item in data["output2"][:top_n]:
                try:
                    price = float(item.get("last", 0))
                    if price < 1:
                        continue
                    results.append({
                        "symbol": item.get("symb", ""),
                        "name": item.get("name", ""),
                        "price": price,
                        "change_pct": float(item.get("rate", 0)),
                        "volume": int(item.get("tvol", 0)),
                        "exchange": exchange,
                        "source": "rise_rank" if sort == "1" else "fall_rank",
                    })
                except (ValueError, TypeError):
                    continue
            return results
    except Exception as e:
        logger.debug("Rise/fall rank fetch error: {}", e)
    return []


def get_volume_increase_rank(exchange: str = "NAS", top_n: int = 30) -> List[Dict]:
    """해외주식 거래증가율순위
    
    Returns stocks ranked by volume increase rate.
    Used for: detecting unusual volume patterns.
    """
    auth = get_auth()
    _rate_limit()
    headers = auth.get_headers(tr_id="HHDFS76950800")
    params = {"AUTH": "", "EXCD": exchange, "BYMD": "", "MODP": "0"}
    
    try:
        resp = requests.get(
            f"{config.BASE_URL}/uapi/overseas-price/v1/quotations/inquire-volume-increase",
            headers=headers, params=params, timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("rt_cd") == "0" and data.get("output2"):
            results = []
            for item in data["output2"][:top_n]:
                try:
                    price = float(item.get("last", 0))
                    if price < 1:
                        continue
                    results.append({
                        "symbol": item.get("symb", ""),
                        "name": item.get("name", ""),
                        "price": price,
                        "change_pct": float(item.get("rate", 0)),
                        "volume": int(item.get("tvol", 0)),
                        "vol_increase_rate": float(item.get("vol_rate", item.get("vrte", 0))),
                        "exchange": exchange,
                        "source": "vol_increase",
                    })
                except (ValueError, TypeError):
                    continue
            return results
    except Exception as e:
        logger.debug("Volume increase rank fetch error: {}", e)
    return []


# ==============================================
# yf.download() 호환 Drop-in 대체
# ==============================================

def download(tickers: Union[str, List[str]], 
             period: str = "1mo",
             interval: str = "1d",
             start: str = None,
             end: str = None,
             progress: bool = False,
             auto_adjust: bool = True,
             **kwargs) -> pd.DataFrame:
    """yf.download() 호환 함수
    
    기존 코드에서 `import yfinance as yf` → `import kis_data as yf` 로만 바꾸면
    나머지 코드는 수정 없이 동작.
    
    Args:
        tickers: 종목코드(들). "AAPL" 또는 ["AAPL", "MSFT"]
        period: "5d", "1mo", "3mo", "6mo", "1y", "2y" 등
        interval: "1d" 만 지원 (일봉). 분봉은 무시하고 일봉으로 대체.
        start/end: 날짜범위 (period 대신 사용 시)
        progress: 무시 (호환용)
        auto_adjust: 수정주가 반영
    
    Returns:
        pd.DataFrame (yfinance 출력과 동일한 구조)
    """
    # Handle single ticker vs multi-ticker
    if isinstance(tickers, str):
        ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]
        if len(ticker_list) == 1:
            # Special handling for index symbols
            symbol = ticker_list[0]
            
            # 지수 심볼은 KIS에서 직접 지원 안 됨 → 빈 DataFrame 반환
            if symbol.startswith("^"):
                logger.debug("Index symbol {} not supported by KIS API, returning empty", symbol)
                return pd.DataFrame()
            
            # Check interval
            if interval.endswith("m") or interval.endswith("h"):
                int_map = {
                    "1m": "1", "2m": "1", "5m": "5", "15m": "15", 
                    "30m": "30", "60m": "60", "1h": "60", "90m": "60"
                }
                kis_interval = int_map.get(interval, "15")
                df = get_intraday_ohlcv(symbol, interval_mins=kis_interval, max_records=120)
            else:
                # Period → days 변환 (Daily fallback)
                days = _period_to_days(period, start, end)
                df = get_daily_ohlcv(symbol, days=days, adjusted=auto_adjust)
                
            if df is None or df.empty:
                return pd.DataFrame()
            
            # yfinance 호환: Adj Close 추가
            if "Close" in df.columns:
                df["Adj Close"] = df["Close"]
            
            return df
    else:
        ticker_list = list(tickers)
    
    # Multi-ticker: download each and combine
    if len(ticker_list) > 1:
        all_data = {}
        for symbol in ticker_list:
            if symbol.startswith("^"):
                continue  # 지수 skip
                
            if interval.endswith("m") or interval.endswith("h"):
                int_map = {"1m": "1", "5m": "5", "15m": "15", "30m": "30", "60m": "60", "1h": "60"}
                kis_interval = int_map.get(interval, "15")
                df = get_intraday_ohlcv(symbol, interval_mins=kis_interval, max_records=120)
            else:
                days = _period_to_days(period, start, end)
                df = get_daily_ohlcv(symbol, days=days, adjusted=auto_adjust)
                
            if df is not None and not df.empty:
                all_data[symbol] = df
        
        if not all_data:
            return pd.DataFrame()
        
        # Combine into MultiIndex columns like yfinance
        if len(all_data) == 1:
            return list(all_data.values())[0]
        
        combined = pd.concat(all_data, axis=1)
        # Swap levels to match yfinance format: (Price, Ticker)
        if isinstance(combined.columns, pd.MultiIndex):
            combined = combined.swaplevel(axis=1)
        return combined
    
    # Single ticker from list
    return download(ticker_list[0], period=period, interval=interval,
                    start=start, end=end, auto_adjust=auto_adjust, **kwargs)


def _period_to_days(period: str, start: str = None, end: str = None) -> int:
    """yfinance period string → 일수 변환"""
    if start:
        try:
            start_dt = pd.Timestamp(start)
            end_dt = pd.Timestamp(end) if end else pd.Timestamp.now()
            return max((end_dt - start_dt).days + 10, 30)  # buffer
        except:
            return 100
    
    period_map = {
        "1d": 5,
        "5d": 10,
        "1wk": 10,
        "1mo": 30,
        "3mo": 100,   # KIS max per call  
        "6mo": 100,
        "1y": 100,
        "2y": 100,
        "5y": 100,
    }
    return period_map.get(period, 100)


# ==============================================
# Ticker class (yfinance.Ticker 호환)
# ==============================================

class Ticker:
    """yfinance.Ticker 호환 클래스
    
    Usage:
        t = kis_data.Ticker("AAPL")
        print(t.info['currentPrice'])
    """
    
    def __init__(self, symbol: str):
        self.symbol = symbol.upper()
        self._info = None
        self._history = None
    
    @property
    def info(self) -> dict:
        """종목 기본 정보 (yfinance.Ticker.info 호환)"""
        if self._info is None:
            price_data = get_current_price(self.symbol)
            if price_data:
                self._info = {
                    "symbol": self.symbol,
                    "currentPrice": price_data["last"],
                    "previousClose": price_data["base"],
                    "open": price_data["open"],
                    "dayHigh": price_data["high"],
                    "dayLow": price_data["low"],
                    "volume": price_data["tvol"],
                    "regularMarketVolume": price_data["tvol"],
                    "averageVolume": price_data["pvol"],
                    "regularMarketPrice": price_data["last"],
                    "regularMarketPreviousClose": price_data["base"],
                    "regularMarketChange": price_data["diff"],
                    "regularMarketChangePercent": price_data["rate"],
                    # 아래는 KIS에서 직접 제공 안 됨 → 기본값
                    "shortRatio": 0,
                    "floatShares": 0,
                    "sharesShort": 0,
                    "shortPercentOfFloat": 0,
                    "marketCap": 0,
                    "trailingPE": 0,
                    "forwardPE": 0,
                    "fiftyTwoWeekHigh": 0,
                    "fiftyTwoWeekLow": 0,
                }
            else:
                self._info = {"symbol": self.symbol}
        return self._info
    
    def history(self, period: str = "1mo", interval: str = "1d", **kwargs) -> pd.DataFrame:
        """종목 히스토리 (yfinance.Ticker.history 호환)"""
        days = _period_to_days(period)
        df = get_daily_ohlcv(self.symbol, days=days)
        if df is None:
            return pd.DataFrame()
        df["Adj Close"] = df["Close"]
        return df


# ==============================================
# Utility
# ==============================================

def get_batch_prices(symbols: List[str]) -> Dict[str, Dict]:
    """여러 종목 현재가 일괄 조회 (rate limit 준수)
    
    Args:
        symbols: 종목코드 리스트
    
    Returns:
        {symbol: price_data_dict}
    """
    results = {}
    for symbol in symbols:
        data = get_current_price(symbol)
        if data:
            results[symbol] = data
    return results


# ==============================================
# Self Test
# ==============================================

if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")
    
    print("=" * 60)
    print("KIS Data Provider — Self Test")
    print("=" * 60)
    
    # Test 1: 현재가
    print("\n[1] 현재가 조회 (AAPL)")
    price = get_current_price("AAPL")
    if price:
        print(f"  ✅ AAPL: ${price['last']} (전일: ${price['base']}, "
              f"변동: {price['rate']}%, 거래량: {price['tvol']:,})")
    else:
        print("  ❌ 현재가 조회 실패")
    
    # Test 2: 일봉
    print("\n[2] 일봉 OHLCV 조회 (AAPL, 30일)")
    df = get_daily_ohlcv("AAPL", days=30)
    if df is not None and not df.empty:
        print(f"  ✅ {len(df)}건 조회 완료")
        print(f"  최근 3일:\n{df.tail(3)}")
    else:
        print("  ❌ 일봉 조회 실패")
    
    # Test 3: yf.download() 호환
    print("\n[3] download() 호환 테스트 (MSFT, period='1mo')")
    df2 = download("MSFT", period="1mo", progress=False)
    if not df2.empty:
        print(f"  ✅ {len(df2)}건, columns: {list(df2.columns)}")
    else:
        print("  ❌ download() 실패")
    
    # Test 4: 거래량 순위
    print("\n[4] 거래량 순위 (NASDAQ)")
    rankings = get_volume_rank("NAS", top_n=5)
    if rankings:
        print(f"  ✅ {len(rankings)}개 종목:")
        for r in rankings[:5]:
            print(f"    {r['symbol']:8s} ${r['price']:>8.2f}  "
                  f"Vol: {r['volume']:>12,}  {r['change_pct']:>+6.2f}%")
    else:
        print("  ❌ 거래량 순위 조회 실패")
    
    print("\n" + "=" * 60)
    print("Self test complete!")
