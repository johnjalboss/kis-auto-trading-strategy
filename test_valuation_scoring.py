import sys
from loguru import logger
from fundamental_analyzer import FundamentalAnalyzer

logger.remove()
logger.add(sys.stderr, level="INFO", colorize=True,
           format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")

print("Testing new Valuation Scoring (Sector PE & PEG Integration)...")
fa = FundamentalAnalyzer()

tickers = ["AAPL", "NVDA", "WPC", "XOM", "SO"]

for sym in tickers:
    print(f"\n{'='*50}")
    print(f"Ticker: {sym}")
    print('='*50)
    
    try:
        f = fa.analyze(sym)
        print(f"  Sector: {f.details if 'NO_PEG_DATA' not in f.details else 'N/A'}")
        print(f"  PE Ratio: {f.pe_ratio:.2f}")
        print(f"  PEG Ratio: {f.peg_ratio:.2f}")
        print(f"  Value Score: {f.value_score} / 100")
        print(f"  Quality Score: {f.quality_score} / 100")
        print(f"  Growth Score: {f.growth_score} / 100")
        print(f"  Overall Score: {f.overall_score} / 100")
        print(f"  Recommendation: {f.recommendation}")
        print(f"  Details: {f.details}")
    except Exception as e:
        print(f"  Failed to analyze {sym}: {e}")
