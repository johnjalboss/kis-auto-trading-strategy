import sys, os
from dotenv import load_dotenv
import time
from loguru import logger

# Reconfigure stdout to handle UTF-8 safely
sys.stdout.reconfigure(encoding='utf-8')

# Force working directory
current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)
sys.path.insert(0, current_dir)

load_dotenv()

# Setup test log format
logger.remove()
logger.add(sys.stderr, level="INFO")

# Import shimmed yfinance (data_proxy shims yf upon import)
import data_proxy
from fundamental_analyzer import FundamentalAnalyzer
from crypto_sentiment import CryptoSentimentIndicator
from fred_macro import get_fred_analyzer

def run_tests():
    print("=" * 60)
    print("INTEGRATION & FALLBACK SYSTEM TEST")
    print("=" * 60)
    
    # 1. Test FRED Macro
    print("\n[1/4] Testing FRED Macro Analyzer...")
    try:
        fa = get_fred_analyzer()
        res = fa.analyze()
        print(f"  Score: {res['score']}")
        print(f"  T10Y2Y: {res['t10y2y']}% | FEDFUNDS: {res['fedfunds']}%")
        print(f"  Signals: {res['signals']}")
        print(f"  Reason: {res['reason']}")
    except Exception as e:
        print(f"  ❌ FRED Error: {e}")
        
    # 2. Test Crypto Sentiment
    print("\n[2/4] Testing Crypto Sentiment (Alternative.me Index + BTC)...")
    try:
        cs = CryptoSentimentIndicator()
        res = cs.analyze()
        print(f"  BTC Price: ${res.btc_price:,.2f}")
        print(f"  24h Change: {res.btc_change_24h:+.2f}% | 7d: {res.btc_change_7d:+.2f}%")
        print(f"  Final Sentiment Score: {res.sentiment_score}/100 ({res.sentiment})")
        print(f"  Recommendation: {res.recommendation}")
    except Exception as e:
        print(f"  ❌ Crypto Sentiment Error: {e}")
        
    # 3. Test Fundamental Analyzer & Fallback layers
    print("\n[3/4] Testing Fundamental Analyzer (AAPL & NVDA)...")
    analyzer = FundamentalAnalyzer()
    
    # Apple test
    print("\nAnalyzing AAPL (First run - Live query / File cache update)...")
    t0 = time.time()
    res_aapl = analyzer.analyze("AAPL")
    t1 = time.time()
    print(f"  Done in {t1-t0:.2f} seconds.")
    print(f"  PE: {res_aapl.pe_ratio:.1f} | PB: {res_aapl.price_to_book:.1f} | ROE: {res_aapl.roe:.1f}%")
    print(f"  Scores: Value={res_aapl.value_score} | Quality={res_aapl.quality_score} | Growth={res_aapl.growth_score}")
    print(f"  Overall Score: {res_aapl.overall_score} ({res_aapl.recommendation})")
    print(f"  Details: {res_aapl.details}")
    
    # NVDA test
    print("\nAnalyzing NVDA (First run - Live query / File cache update)...")
    t0 = time.time()
    res_nvda = analyzer.analyze("NVDA")
    t1 = time.time()
    print(f"  Done in {t1-t0:.2f} seconds.")
    print(f"  PE: {res_nvda.pe_ratio:.1f} | PB: {res_nvda.price_to_book:.1f} | ROE: {res_nvda.roe:.1f}%")
    print(f"  Scores: Value={res_nvda.value_score} | Quality={res_nvda.quality_score} | Growth={res_nvda.growth_score}")
    print(f"  Overall Score: {res_nvda.overall_score} ({res_nvda.recommendation})")
    print(f"  Details: {res_nvda.details}")
    
    # 4. Test Caching (Second run)
    print("\n[4/4] Testing Caching (Second run)...")
    print("\nAnalyzing AAPL (Second run - Should be instant cache hit)...")
    t0 = time.time()
    res_aapl_cached = analyzer.analyze("AAPL")
    t1 = time.time()
    print(f"  Done in {t1-t0:.4f} seconds.")
    print(f"  Overall Score: {res_aapl_cached.overall_score} ({res_aapl_cached.recommendation})")
    
    print("\nAnalyzing NVDA (Second run - Should be instant cache hit)...")
    t0 = time.time()
    res_nvda_cached = analyzer.analyze("NVDA")
    t1 = time.time()
    print(f"  Done in {t1-t0:.4f} seconds.")
    print(f"  Overall Score: {res_nvda_cached.overall_score} ({res_nvda_cached.recommendation})")
    
    print("=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
