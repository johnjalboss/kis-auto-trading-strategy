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
    "BRK.B", "BRK-B", "BLK", "SCHW", "ICE", "CME", "SPGI", "MCO",
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
    """S&P 500 구성종목 반환.

    Oracle Cloud VM은 Wikipedia에서 HTTP 403으로 차단되므로
    완전한 정적 목록을 하드코딩 (2025년 기준 S&P 500).
    네트워크 fetch 먼저 시도, 실패 시 정적 목록 사용.
    """
    # ── 완전한 S&P 500 정적 목록 (Wikipedia 차단 대비 fallback) ──────────────
    # ★ [v3.1.0 PRIORITY MARKET LEADERS]
    # Place top volume & momentum leaders at the front so they are NEVER truncated by candidates[:100]
    SP500_STATIC = [
        "NVDA", "AAPL", "MSFT", "TSLA", "AMD", "QQQ", "TQQQ", "SOXL", "PLTR", "AVGO", "META", "GOOGL", "AMZN", "ARM", "MU", "NFLX", "SOXX", "SPY", "DIA", "IWM", "XLK", "XLI", "XLF",
        "A", "AAL", "ABBV", "ABNB", "ABT", "ACGL", "ACN", "ADBE", "ADI", "ADM",
        "ADP", "ADSK", "AEE", "AEP", "AES", "AFL", "AIG", "AIZ", "AJG", "AKAM",
        "ALB", "ALGN", "ALL", "ALLE", "AMAT", "AMCR", "AME", "AMGN", "AMP",
        "AMT", "ANET", "AON", "AOS", "APA", "APD", "APH", "APO", "APP",
        "APTV", "ARE", "ARES", "ATO", "AVB", "AVY", "AWK", "AXON", "AXP",
        "AZO", "BA", "BAC", "BALL", "BAX", "BBY", "BDX", "BEN", "BFB", "BG",
        "BIIB", "BKNG", "BKR", "BLDR", "BLK", "BMY", "BNY", "BR", "BRK-B", "BRO",
        "BSX", "BX", "BXP", "C", "CAG", "CAH", "CARR", "CASY", "CAT", "CB",
        "CBOE", "CBRE", "CCI", "CCL", "CDNS", "CDW", "CEG", "CF", "CFG", "CHD",
        "CHRW", "CHTR", "CI", "CIEN", "CINF", "CL", "CLX", "CMCSA", "CME", "CMG",
        "CMI", "CMS", "CNC", "CNP", "COF", "COHR", "COIN", "COO", "COP", "COR",
        "COST", "CPAY", "CPB", "CPRT", "CPT", "CRH", "CRL", "CRM", "CRWD", "CSCO",
        "CSGP", "CSX", "CTAS", "CTSH", "CTVA", "CVNA", "CVS", "CVX", "D", "DAL",
        "DASH", "DD", "DDOG", "DE", "DECK", "DELL", "DG", "DGX", "DHI", "DHR",
        "DIS", "DLR", "DLTR", "DOC", "DOV", "DOW", "DPZ", "DRI", "DTE", "DUK",
        "DVA", "DVN", "DXCM", "EA", "EBAY", "ECL", "ED", "EFX", "EG", "EIX",
        "EL", "ELV", "EME", "EMR", "EOG", "EPAM", "EQIX", "EQR", "EQT", "ERIE",
        "ES", "ESS", "ETN", "ETR", "EVRG", "EW", "EXC", "EXE", "EXPD", "EXPE",
        "EXR", "F", "FANG", "FAST", "FCX", "FDS", "FDX", "FE", "FFIV", "FICO",
        "FIS", "FISV", "FITB", "FIX", "FOX", "FOXA", "FRT", "FSLR", "FTNT", "FTV",
        "GD", "GDDY", "GE", "GEHC", "GEN", "GEV", "GILD", "GIS", "GL", "GLW",
        "GM", "GNRC", "GOOG", "GOOGL", "GPC", "GPN", "GRMN", "GS", "GWW", "HAL",
        "HAS", "HBAN", "HCA", "HD", "HIG", "HII", "HLT", "HON", "HOOD", "HPE",
        "HPQ", "HRL", "HSIC", "HST", "HSY", "HUBB", "HUM", "HWM", "IBKR", "IBM",
        "ICE", "IDXX", "IEX", "IFF", "INCY", "INTC", "INTU", "INVH", "IP", "IQV",
        "IR", "IRM", "ISRG", "IT", "ITW", "IVZ", "J", "JBHT", "JBL", "JCI",
        "JKHY", "JNJ", "JPM", "KDP", "KEY", "KEYS", "KHC", "KIM", "KKR", "KLAC",
        "KMB", "KMI", "KO", "KR", "KVUE", "L", "LDOS", "LEN", "LH", "LHX",
        "LII", "LIN", "LITE", "LLY", "LMT", "LNT", "LOW", "LRCX", "LULU", "LUV",
        "LVS", "LYB", "LYV", "MA", "MAA", "MAR", "MAS", "MCD", "MCHP", "MCK",
        "MCO", "MDLZ", "MDT", "MET", "META", "MGM", "MKC", "MLM", "MMM", "MNST",
        "MO", "MOS", "MPC", "MPWR", "MRK", "MRNA", "MRSH", "MS", "MSCI", "MSFT",
        "MSI", "MTB", "MTD", "MU", "NCLH", "NDAQ", "NDSN", "NEE", "NEM", "NFLX",
        "NI", "NKE", "NOC", "NOW", "NRG", "NSC", "NTAP", "NTRS", "NUE", "NVDA",
        "NVR", "NWS", "NWSA", "NXPI", "O", "ODFL", "OKE", "OMC", "ON", "ORCL",
        "ORLY", "OTIS", "OXY", "PANW", "PAYX", "PCAR", "PCG", "PEG", "PEP", "PFE",
        "PFG", "PG", "PGR", "PH", "PHM", "PKG", "PLD", "PLTR", "PM", "PNC",
        "PNR", "PNW", "PODD", "POOL", "PPG", "PPL", "PRU", "PSA", "PSKY", "PSX",
        "PTC", "PWR", "PYPL", "Q", "QCOM", "RCL", "REG", "REGN", "RF", "RJF",
        "RL", "RMD", "ROK", "ROL", "ROP", "ROST", "RSG", "RTX", "RVTY", "SATS",
        "SBAC", "SBUX", "SCHW", "SHW", "SJM", "SLB", "SMCI", "SNA", "SNDK", "SNPS",
        "SO", "SOLV", "SPG", "SPGI", "SRE", "STE", "STLD", "STT", "STX", "STZ",
        "SW", "SWK", "SWKS", "SYF", "SYK", "SYY", "T", "TAP", "TDG", "TDY",
        "TECH", "TEL", "TER", "TFC", "TGT", "TJX", "TKO", "TMO", "TMUS", "TPL",
        "TPR", "TRGP", "TRMB", "TROW", "TRV", "TSCO", "TSLA", "TSN", "TT", "TTD",
        "TTWO", "TXN", "TXT", "TYL", "UAL", "UBER", "UDR", "UHS", "ULTA", "UNH",
        "UNP", "UPS", "URI", "USB", "V", "VEEV", "VICI", "VLO", "VLTO", "VMC",
        "VRSK", "VRSN", "VRT", "VRTX", "VST", "VTR", "VTRS", "VZ", "WAB", "WAT",
        "WBD", "WDAY", "WDC", "WEC", "WELL", "WFC", "WM", "WMB", "WMT", "WRB",
        "WSM", "WST", "WTW", "WY", "WYNN", "XEL", "XOM", "XYL", "XYZ", "YUM",
        "ZBH", "ZBRA", "ZTS",
    ]

    # 1) 네트워크 fetch 시도 (성공하면 최신 목록 우선)
    try:
        import pandas as pd
        import urllib.request
        req = urllib.request.Request(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            headers={"User-Agent": "Mozilla/5.0 (compatible; trading-bot/1.0)"}
        )
        html = urllib.request.urlopen(req, timeout=10).read()
        import io
        tables = pd.read_html(io.BytesIO(html))
        df = tables[0]
        symbols = df["Symbol"].str.replace(".", "", regex=False).tolist()
        if len(symbols) > 400:
            logger.info("S&P 500: {} symbols from Wikipedia (live)", len(symbols))
            return symbols
    except Exception as e:
        logger.warning("Wikipedia S&P500 fetch failed (using static list): {}", e)

    # 2) 정적 목록 사용
    logger.info("S&P 500: {} symbols from static list", len(SP500_STATIC))
    return SP500_STATIC


def _fetch_russell1000_tickers() -> list:
    """Russell 1000 구성종목 가져오기 (S&P500 + 추가 대형주)"""
    symbols = set()
    
    # 1) S&P 500 (핵심)
    sp500 = _fetch_sp500_from_wikipedia()
    symbols.update(sp500)
    
    # 2) Russell 1000 중 S&P500에 없는 주요 종목 추가
    additional_russell = [
        "AA", "AAL", "AAMI", "AAON", "AAP", "AAT", "ABCB", "ABG", "ABM", "ABR",
        "ACA", "ACAD", "ACHC", "ACI", "ACIW", "ACLS", "ACM", "ACMR", "ACT", "ADAM",
        "ADC", "ADEA", "ADMA", "ADNT", "ADT", "ADUS", "AEIS", "AEO", "AESI", "AFG",
        "AFRM", "AGCO", "AGNT", "AGO", "AGX", "AGYS", "AHCO", "AHR", "AIN", "AIR",
        "AIT", "AKR", "ALG", "ALGM", "ALGT", "ALHC", "ALK", "ALKS", "ALLY", "ALRM",
        "ALV", "AM", "AMG", "AMH", "AMKR", "AMN", "AMPH", "AMR", "AMRX", "AMSF",
        "AMTM", "AMWD", "AN", "ANDE", "ANF", "ANIP", "AORT", "AOSL", "APAM", "APG",
        "APLE", "APOG", "APPF", "AR", "ARCB", "ARI", "ARLO", "ARMK", "AROC", "ARR",
        "ARW", "ARWR", "ASB", "ASH", "ASO", "ASTE", "ASTH", "ASTS", "ATEN", "ATI",
        "ATMU", "ATR", "AUB", "AVA", "AVAV", "AVNS", "AVNT", "AVT", "AVTR", "AWI",
        "AWR", "AX", "AXTA", "AYI", "AZTA", "AZZ", "BAH", "BANC", "BANF", "BANR",
        "BBT", "BBWI", "BC", "BCC", "BCO", "BCPC", "BDC", "BFAM", "BFH", "BFS",
        "BGC", "BHE", "BHF", "BILL", "BIO", "BJ", "BJRI", "BKE", "BKH", "BKU",
        "BL", "BLD", "BLFS", "BLKB", "BMI", "BMRN", "BNL", "BOH", "BOOT", "BOX",
        "BRBR", "BRC", "BRKR", "BROS", "BRX", "BSY", "BTSG", "BTU", "BURL", "BWA",
        "BWXT", "BXMT", "BYD", "CABO", "CACI", "CAKE", "CALM", "CALX", "CALY", "CAR",
        "CARG", "CART", "CASH", "CATY", "CAVA", "CBRL", "CBSH", "CBT", "CBU", "CC",
        "CCK", "CCOI", "CCS", "CDP", "CE", "CELH", "CENT", "CENTA", "CENX", "CERT",
        "CFFN", "CFLT", "CFR", "CG", "CGNX", "CHCO", "CHDN", "CHE", "CHEF", "CHH",
        "CHRD", "CHWY", "CLB", "CLF", "CLH", "CLSK", "CMC", "CNH", "CNK", "CNM",
        "CNMD", "CNO", "CNR", "CNS", "CNX", "CNXC", "CNXN", "COCO", "COHU", "COKE",
        "COLB", "COLL", "COLM", "CON", "CORT", "COTY", "CPF", "CPK", "CPNG", "CPRI",
        "CPRX", "CR", "CRBG", "CRC", "CRGY", "CRI", "CRK", "CROX", "CRS", "CRSR",
        "CRUS", "CRVL", "CSL", "CSR", "CSW", "CTKB", "CTRE", "CTS", "CUBE", "CUBI",
        "CURB", "CUZ", "CVBF", "CVCO", "CVI", "CVLT", "CVSA", "CW", "CWEN", "CWENA",
        "CWK", "CWST", "CWT", "CXM", "CXT", "CXW", "CYTK", "CZR", "DAN", "DAR",
        "DBD", "DBX", "DCH", "DCI", "DCOM", "DEA", "DEI", "DFH", "DFIN", "DGII",
        "DINO", "DIOD", "DKS", "DLB", "DLX", "DNOW", "DOCN", "DOCS", "DOCU", "DORM",
        "DRH", "DT", "DTM", "DUOL", "DV", "DXC", "DXPE", "DY", "EAT", "ECG",
        "ECPG", "EEFT", "EFC", "EFOR", "EGBN", "EGP", "EHC", "EIG", "ELAN", "ELF",
        "ELS", "EMBC", "EMN", "ENOV", "ENPH", "ENR", "ENS", "ENSG", "ENTG", "ENVA",
        "EPAC", "EPC", "EPR", "EPRT", "EQH", "ESAB", "ESE", "ESI", "ESNT", "ETD",
        "ETSY", "EVR", "EVTC", "EWBC", "EXEL", "EXLS", "EXP", "EXPO", "EXTR", "EYE",
        "EZPW", "FAF", "FBIN", "FBK", "FBNC", "FBP", "FBRT", "FCF", "FCFS", "FCN",
        "FCPT", "FDP", "FELE", "FFBC", "FFIN", "FG", "FHB", "FHI", "FHN", "FIBK",
        "FIVE", "FIZZ", "FLEX", "FLG", "FLO", "FLR", "FLS", "FMC", "FN", "FNB",
        "FND", "FNF", "FORM", "FOUR", "FOXF", "FR", "FRPT", "FSS", "FTDR", "FTI",
        "FTRE", "FUL", "FULT", "FUN", "FWRD", "G", "GAP", "GATX", "GBCI", "GBX",
        "GDYN", "GEF", "GEO", "GFF", "GGG", "GHC", "GIII", "GKOS", "GLPI", "GME",
        "GMED", "GNL", "GNTX", "GNW", "GO", "GOGO", "GOLF", "GPI", "GPK", "GRBK",
        "GSHD", "GT", "GTES", "GTLS", "GTM", "GTY", "GVA", "GWRE", "GXO", "H",
        "HAE", "HAFC", "HALO", "HASI", "HAYW", "HCC", "HCI", "HCSG", "HE", "HFWA",
        "HGV", "HIMS", "HIW", "HL", "HLI", "HLIT", "HLNE", "HLX", "HMN", "HNI",
        "HOG", "HOMB", "HOPE", "HQY", "HR", "HRB", "HWC", "HXL", "IBOC", "IDA",
        "IDCC", "ILMN", "INGR", "IPGP", "IRT", "ITT", "JAZZ", "JEF", "JHG", "JLL",
        "KBH", "KBR", "KD", "KEX", "KNF", "KNSL", "KNX", "KRC", "KRG", "KTOS",
        "LAD", "LAMR", "LCID", "LEA", "LECO", "LFUS", "LIVN", "LNTH", "LOPE", "LPX",
        "LSCC", "LSTR", "M", "MANH", "MASI", "MAT", "MDB", "MEDP", "MELI", "MIDD",
        "MKSI", "MLI", "MMS", "MOGA", "MORN", "MP", "MSA", "MSM", "MSTR", "MTDR",
        "MTG", "MTN", "MTSI", "MTZ", "MUR", "MUSA", "MZTI", "NBIX", "NET", "NEU",
        "NFG", "NJR", "NLY", "NNN", "NOV", "NOVT", "NSA", "NTNX", "NVST", "NVT",
        "NWE", "NXST", "NXT", "NYT", "OC", "OGE", "OGS", "OHI", "OKTA", "OLED",
        "OLLI", "OLN", "ONB", "ONTO", "OPCH", "ORA", "ORI", "OSK", "OVV", "OZK",
        "P", "PAG", "PATH", "PB", "PBF", "PCTY", "PEGA", "PEN", "PFGC", "PII",
        "PINS", "PK", "PLNT", "PNFP", "POR", "POST", "PPC", "PR", "PRI", "PSN",
        "PVH", "QLYS", "QS", "R", "RBA", "RBC", "REXR", "RGA", "RGEN", "RGLD",
        "RH", "RIVN", "RKLB", "RLI", "RMBS", "RNR", "ROIV", "RPM", "RRC", "RRX",
        "RS", "RYAN", "RYN", "SAIA", "SAIC", "SAM", "SARO", "SBRA", "SCI", "SE",
        "SEIC", "SF", "SFM", "SGI", "SHC", "SHOP", "SIGI", "SITM", "SLAB", "SLGN",
        "SLM", "SMG", "SN", "SNOW", "SNX", "SOFI", "SOLS", "SON", "SPXC", "SR",
        "SSB", "SSD", "ST", "STAG", "STRL", "STWD", "SWX", "SYNA", "TCBI", "TEX",
        "THC", "THG", "THO", "TKR", "TLN", "TMHC", "TNL", "TOL", "TREX", "TRU",
        "TTC", "TTEK", "TTMI", "TWLO", "TXNM", "TXRH", "UBSI", "UFPI", "UGI", "ULS",
        "UMBF", "UNM", "USFD", "UTHR", "VAL", "VC", "VFC", "VICR", "VLY", "VMI",
        "VNO", "VNOM", "VNT", "VOYA", "VVV", "WAL", "WBS", "WCC", "WEX", "WFRD",
        "WH", "WHR", "WING", "WLK", "WMG", "WMS", "WPC", "WSO", "WTFC", "WTRG",
        "WTS", "WWD", "XPO", "XRAY", "YETI", "ZION", "ZS",
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
