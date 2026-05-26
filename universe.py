"""
Russell 1000 유니버스 (동적 + 캐시)
====================================
1000대 미국 대형주에서 스크리닝합니다.
- 위키피디아 S&P500 + Russell 1000 ETF(IWB) 기반
- 로컬 캐시 (1주일 유효)
- 거래소 자동 매핑
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger

# ==============================================
# 캐시 설정
# ==============================================

CACHE_FILE = Path("universe_cache.json")
CACHE_DAYS = 7  # 1주일마다 갱신

# ==============================================
# 거래소 매핑 (주요 종목)
# ==============================================

NYSE_SYMBOLS = {
    "JPM", "BAC", "WFC", "GS", "MS", "C", "BK", "USB", "PNC", "TFC",
    "WMT", "HD", "LOW", "TGT", "COST", "DG", "DLTR",
    "JNJ", "PFE", "UNH", "ABT", "TMO", "DHR", "BMY", "LLY", "MRK",
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "VLO", "PSX",
    "DIS", "NKE", "MCD", "SBUX", "YUM", "CMG",
    "KO", "PEP", "PG", "CL", "KMB", "EL", "GIS", "K", "SJM",
    "V", "MA", "AXP", "COF", "DFS", "SYF",
    "BA", "RTX", "LMT", "NOC", "GD", "GE", "HON", "MMM", "CAT", "DE",
    "SPY", "IWM", "DIA", "XLK", "XLP", "XLU", "XLV", "XLY", "XLE", "XLF",
    "T", "VZ", "SO", "DUK", "NEE", "AEP", "D", "SRE",
    "BRK.B", "BRKB", "BLK", "SCHW", "ICE", "CME", "SPGI", "MCO",
    "CRM", "IBM", "ACN", "ORCL",
    "F", "GM",
    "PLD", "AMT", "CCI", "EQIX", "PSA", "SPG",
    "UNP", "CSX", "NSC", "FDX", "UPS",
    # 자주 오류 나는 종목 (NYSE지만 NASD로 기본값 설정 방지)
    "AME", "AIZ", "IRM", "NUE", "RS", "NUE", "FCX", "DD", "DOW",
    "ETN", "EMR", "ITW", "PH", "ROP", "CMI", "DOV", "URI", "PCAR",
    "LIN", "SHW", "APD", "ECL", "VMC", "MLM",
    "WM", "RSG", "AVB", "EQR", "EXR", "MAA", "UDR", "INVH", "CPT",
    "WELL", "VTR", "ARE", "O", "VTR",
}

AMEX_SYMBOLS = {"SQQQ", "TQQQ", "UVXY", "VXX"}


def get_exchange(symbol: str) -> str:
    """종목의 거래소 코드 반환 (주문용)"""
    s = symbol.upper().replace(".", "")
    if s in AMEX_SYMBOLS:
        return "AMEX"
    if s in NYSE_SYMBOLS:
        return "NYSE"
    return "NASD"  # Default — NASDAQ


# ==============================================
# Russell 1000 동적 로딩
# ==============================================

def _fetch_sp500_from_wikipedia() -> list:
    """위키피디아에서 S&P 500 구성종목 가져오기"""
    try:
        import pandas as pd
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        df = tables[0]
        symbols = df["Symbol"].str.replace(".", "-", regex=False).tolist()
        logger.info("S&P 500: {} symbols from Wikipedia", len(symbols))
        return symbols
    except Exception as e:
        logger.warning("Wikipedia S&P500 fetch failed: {}", e)
        return []


def _fetch_russell1000_tickers() -> list:
    """Russell 1000 구성종목 가져오기 (S&P500 + 추가 대형주)"""
    symbols = set()
    
    # 1) S&P 500 (핵심)
    sp500 = _fetch_sp500_from_wikipedia()
    symbols.update(sp500)
    
    # 2) Russell 1000 중 S&P500에 없는 주요 종목 추가
    # (Russell 1000 = S&P500 + 그 아래 500개 중대형주)
    additional_russell = [
        # AI / Tech Growth
        "PLTR", "CRWD", "SNOW", "NET", "DDOG", "ZS", "MDB", "CFLT",
        "PATH", "U", "RBLX", "DUOL", "DOCS", "BILL", "PCOR", "ESTC",
        "GTLB", "BRZE", "TOST", "SAMSARA",
        # Semiconductor
        "SMCI", "ARM", "MRVL", "ON", "WOLF", "CRUS", "DIOD", "ACLS",
        "RMBS", "SITM", "FORM", "POWI",
        # EV / Clean Energy
        "RIVN", "LCID", "NIO", "XPEV", "LI", "QS", "CHPT", "BLNK",
        "FSLR", "ENPH", "SEDG", "RUN",
        # Crypto / Fintech
        "COIN", "MSTR", "MARA", "RIOT", "CLSK", "HUT", "BITF",
        "SOFI", "HOOD", "AFRM", "UPST", "LC", "NU",
        # Biotech
        "MRNA", "BNTX", "CRSP", "BEAM", "EDIT", "NTLA", "EXAS",
        "TWST", "FATE", "IOVA", "ALNY", "INCY",
        # Space / Defense
        "RKLB", "ASTS", "BWXT", "KTOS", "RCAT",
        "PLTR", "LDOS", "SAIC", "BAH",
        # Consumer / E-commerce
        "SHOP", "MELI", "SE", "CPNG", "PINS", "SNAP", "ETSY",
        "W", "CHWY", "RVLV", "BROS", "CAVA", "SHAK",
        # Healthcare / MedTech
        "DXCM", "ISRG", "VEEV", "HIMS", "OSCR", "GDRX",
        "IRTC", "NVCR", "NVAX",
        # Mid-cap Growth
        "CELH", "AXON", "TMDX", "LNTH", "WDAY", "TTD", "ROKU",
        "ZI", "ASAN", "APP", "IONQ", "RGTI", "QUBT",
        # Energy / Materials
        "FANG", "DVN", "OXY", "HAL", "BKR", "CTRA",
        "FCX", "AA", "CLF", "STLD", "NUE", "RS",
        # Financial Services
        "ACGL", "RGA", "WRB", "AIZ", "GL", "KNSL",
        "LPLA", "RJF", "IBKR", "MKTX", "VIRT",
        # REITs
        "O", "VTR", "WELL", "IRM", "DLR", "ARE",
        # Industrials
        "GNRC", "TT", "IR", "XYL", "ROK", "AME", "NDSN",
        "PAYC", "PAYX", "ADP",
        # Media / Entertainment
        "WBD", "LYV", "IMAX", "MTCH", "BMBL",
        # Travel / Leisure
        "ABNB", "BKNG", "EXPE", "MAR", "HLT", "H",
        "DAL", "UAL", "LUV", "AAL", "ALK", "JBLU",
        # Food / Beverage
        "MNST", "SAM", "COKE",
        # Automotive / Industrial
        "TSLA", "RIVN", "TER", "ANET", "KEYS",
    ]
    symbols.update(additional_russell)
    
    # 중복/빈값 제거 & 정렬
    symbols = sorted([s.strip() for s in symbols if s and s.strip()])
    
    # 마침표가 있는 심볼을 KIS API 형식으로 변환 (BRK.B -> BRKB)
    cleaned = []
    for s in symbols:
        clean = s.replace(".", "").replace("-", "")
        if clean and len(clean) <= 5:  # 합리적 길이
            cleaned.append(clean)
        else:
            cleaned.append(s.replace(".", "").replace("-", "")[:5])
    
    # 중복 제거
    cleaned = sorted(set(cleaned))
    
    logger.info("Russell 1000 universe: {} symbols", len(cleaned))
    return cleaned


# ==============================================
# 캐시 관리
# ==============================================

def _save_cache(symbols: list):
    """유니버스 캐시 저장"""
    data = {
        "updated": datetime.now().isoformat(),
        "count": len(symbols),
        "symbols": symbols
    }
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    logger.info("Universe cache saved: {} symbols", len(symbols))


def _load_cache() -> list:
    """유니버스 캐시 로드 (유효기간 내)"""
    if not CACHE_FILE.exists():
        return []
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        updated = datetime.fromisoformat(data["updated"])
        if datetime.now() - updated > timedelta(days=CACHE_DAYS):
            logger.info("Universe cache expired, refreshing...")
            return []
        logger.info("Universe loaded from cache: {} symbols", data["count"])
        return data["symbols"]
    except Exception as e:
        logger.warning("Cache load failed: {}", e)
        return []


# ==============================================
# 핵심 유니버스 (네트워크 차단 시 폴백) & 빅테크/우량주 백업 리스트
# ==============================================

CORE_UNIVERSE = [
    # Mega Cap Tech (빅테크)
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "ORCL", "CRM",
    # Semiconductor (반도체)
    "AMD", "INTC", "QCOM", "TXN", "MU", "LRCX", "KLAC", "AMAT", "MRVL", "SMCI", "ARM", "ASML", "TSM",
    "ON", "LSCC", "MPWR", "AMKR", "MCHP",
    # Software / Cloud (클라우드/소프트웨어)
    "ADBE", "NOW", "INTU", "SNOW", "PLTR", "NET", "CRWD", "DDOG", "ZS", "PANW", "FTNT", "WDAY", "TEAM",
    "VEEV", "ANET", "CDNS", "SNPS", "TYL", "PTC", "EPAM", "IT",
    # AI / Quantum (신성장)
    "IONQ", "RGTI", "APP", "PATH", "TTD", "ROKU",
    # E-commerce / Consumer (이커머스/컨슈머 테크)
    "SHOP", "MELI", "BKNG", "ABNB", "CPNG", "NFLX", "SPOT", "UBER", "DASH",
    # Fintech / Crypto (핀테크/크립토)
    "COIN", "MSTR", "SOFI", "HOOD", "AFRM", "SQ", "PYPL",
    
    # === 방어주 & 전통 우량주 확장 (시장이 불안정할 때 피난처) ===
    # Healthcare / Pharma (헬스케어/제약)
    "LLY", "UNH", "JNJ", "ABBV", "MRK", "PFE", "TMO", "ABT", "ISRG", "DXCM", "DHR", "SYK", "VRTX", "REGN", "AMGN",
    "HUM", "CI", "CNC", "ZTS", "IDXX", "EW", "BDX", "BSX", "MTD", "ILMN", "BIIB", "MCK", "COR", "ZBH",
    # Finance / Banks (금융/은행)
    "JPM", "BAC", "GS", "MS", "V", "MA", "BRK-B", "WFC", "C", "AXP", "BLK", "SCHW", "SPGI", "CME",
    "PGR", "CB", "MMC", "AON", "TRV", "ALL", "AFL", "MET", "PRU", "COF", "DFS", "SYF", "TFC", "USB",
    # Industrial / Defense (산업재/방산 - 지정학적 리스크 헷지)
    "CAT", "DE", "BA", "GE", "HON", "RTX", "LMT", "NOC", "GD", "TDG", "WM", "RSG",
    "UNP", "UPS", "FDX", "CSX", "NSC", "ETN", "EMR", "ITW", "PH", "ROP", "CMI", "DOV", "URI", "PCAR",
    # Consumer Discretionary & Staples (소비재 - 경기 침체 방어)
    "WMT", "COST", "HD", "NKE", "MCD", "SBUX", "KO", "PEP", "PG", "PM", "MO", "TGT", "CL", "KMB",
    "TJX", "ROST", "LULU", "ORLY", "AZO", "TSCO", "YUM", "DRI", "HLT", "MAR", "CMG", "DG", "DLTR", "K", "GIS",
    # Energy (에너지/정유 - 인플레이션 헷지)
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "VLO", "PSX", "OXY",
    "HES", "FANG", "DVN", "PXD", "HAL", "BKR", "WMB", "KMI", "OKE",
    # Utilities & Telecom (유틸리티/통신 - 고배당/안전가치)
    "NEE", "DUK", "SO", "AEP", "SRE", "T", "VZ", "TMUS", "EXC", "XEL", "ED", "PEG", "WEC", "AWK",
    # Real Estate / REITs (리츠)
    "PLD", "AMT", "EQIX", "CCI", "PSA", "O",
    "SPG", "AVB", "EQR", "EXR", "MAA", "UDR", "INVH", "CPT", "WELL", "VTR", "ARE",
    # Materials / Commodity
    "LIN", "SHW", "APD", "ECL", "NUE", "FCX", "STLD", "VMC", "MLM", "CTVA",
    
    # Space / Defense
    "RKLB", "AXON", "KTOS",
    # Biotech
    "MRNA", "CRSP", "BEAM",
]

# 위 Fallback(CORE) 유니버스 종목인지 판별하기 위한 세트
FALLBACK_SYMBOLS = set(CORE_UNIVERSE)


# ==============================================
# Public API
# ==============================================

_universe_cache = None

def get_all_symbols() -> list:
    """전체 유니버스 종목 리스트 반환 (캐시 적용)"""
    global _universe_cache
    
    if _universe_cache:
        return _universe_cache.copy()
    
    # 1) 로컬 캐시
    symbols = _load_cache()
    
    # 2) 동적 로딩
    if not symbols:
        try:
            symbols = _fetch_russell1000_tickers()
            if symbols and len(symbols) > 100:
                _save_cache(symbols)
        except Exception as e:
            logger.error("Dynamic fetch failed: {}", e)
    
    # 3) 폴백
    if not symbols or len(symbols) < 50:
        logger.warning("Using core universe fallback ({} symbols)", len(CORE_UNIVERSE))
        symbols = CORE_UNIVERSE.copy()
    
    _universe_cache = symbols
    
    # Filter out KIS API permanently blacklisted symbols
    try:
        bl_path = Path("kis_symbol_blacklist.json")
        if bl_path.exists():
            import json as _json
            bl_data = _json.loads(bl_path.read_text(encoding="utf-8"))
            blacklist = set(bl_data.get("symbols", []))
            if blacklist:
                before = len(_universe_cache)
                _universe_cache = [s for s in _universe_cache if s.upper() not in blacklist]
                removed = before - len(_universe_cache)
                if removed > 0:
                    logger.info("Universe: filtered {} KIS-blacklisted symbols (remaining: {})",
                               removed, len(_universe_cache))
    except Exception as e:
        logger.debug("Blacklist filter failed: {}", e)
    
    return _universe_cache.copy()


def get_symbol_info(symbol: str) -> dict:
    """종목 정보 반환"""
    return {
        "name": symbol,
        "exchange": get_exchange(symbol),
        "sector": "",
    }


def get_universe_count() -> int:
    """유니버스 종목 수"""
    return len(get_all_symbols())


def refresh_universe():
    """유니버스 강제 갱신"""
    global _universe_cache
    _universe_cache = None
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()
    symbols = get_all_symbols()
    logger.info("Universe refreshed: {} symbols", len(symbols))
    return symbols


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("=" * 50)
    print("📊 Russell 1000 유니버스")
    print("=" * 50)
    
    symbols = get_all_symbols()
    print(f"\n총 {len(symbols)}개 종목")
    print(f"\n처음 20개: {symbols[:20]}")
    print(f"마지막 10개: {symbols[-10:]}")
    
    # 거래소 분포
    exchanges = {}
    for s in symbols:
        ex = get_exchange(s)
        exchanges[ex] = exchanges.get(ex, 0) + 1
    print(f"\n거래소 분포: {exchanges}")
