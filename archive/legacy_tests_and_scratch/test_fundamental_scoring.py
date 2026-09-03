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
        print(f"  T10Y2Y: {res['t10y2y']}% | T10Y3M: {res['t10y3m']}% | FEDFUNDS: {res['fedfunds']}% | Real Yield (DFII10): {res['dfii10']}%")
        print(f"  M2 YoY: {res['m2_yoy']*100:.2f}% | Credit Spread: {res['credit_spread']}% | Fed Assets 3mo: {res['walcl_3mo']*100:.2f}%")
        print(f"  Consumer Sentiment: {res['sentiment']} | Financial Stress Index: {res['financial_stress']} | Sahm Indicator: {res['sahm_recession']}")
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
    
    # 5. Test yfinance Fallback Recovery Simulation
    print("\n[5/5] Testing yfinance Fallback Recovery Simulation (Simulating yfinance block)...")
    import yfinance as yf
    import pandas as pd
    
    # Save original download proxy
    old_download = data_proxy._safe_original_yf_download
    # Force original yfinance download to return empty DataFrame to trigger fallback
    data_proxy._safe_original_yf_download = lambda *args, **kwargs: pd.DataFrame()
    # Reset call limit just in case
    data_proxy._yf_call_count = 0
    
    test_symbols = ["SPY", "^VIX", "BTC-USD", "CL=F", "KRW=X"]
    for sym in test_symbols:
        print(f"\n  Downloading {sym} via proxy (with simulated yfinance block)...")
        try:
            df = yf.download(sym, period="1mo")
            if df is not None and not df.empty:
                print(f"  ✅ SUCCESS: Recovered {sym} DataFrame (len={len(df)})")
                print(f"     Columns: {list(df.columns)}")
                print(f"     Index range: {df.index.min()} to {df.index.max()}")
            else:
                print(f"  ❌ FAILURE: Failed to recover {sym}")
        except Exception as test_err:
            print(f"  ❌ Error testing fallback for {sym}: {test_err}")
            
    # Restore original download proxy
    data_proxy._safe_original_yf_download = old_download

    # 6. Test MACRO_BLIND_POLICY modes (circuit breaker simulation)
    print("\n[6/6] Testing MACRO_BLIND_POLICY Circuit Breaker Modes...")
    from fred_macro import FREDMacroAnalyzer
    import unittest.mock as mock

    _sentinel_error = Exception("Simulated FRED API failure")

    for policy in ["PENALTY", "BLOCK", "NEUTRAL"]:
        os.environ["MACRO_BLIND_POLICY"] = policy
        analyzer_cb = FREDMacroAnalyzer()
        # Patch _fetch_latest_observation and fetch_series_df to always fail
        with mock.patch.object(analyzer_cb, "_fetch_latest_observation", side_effect=_sentinel_error), \
             mock.patch.object(analyzer_cb, "fetch_series_df", side_effect=_sentinel_error):
            try:
                cb_result = analyzer_cb.analyze()
                cb_score = cb_result.get("score")
                cb_signals = cb_result.get("signals", [])
                cb_has_policy_signal = any(f"MACRO_BLIND_{policy}" in s for s in cb_signals)
                status_icon = "✅" if cb_has_policy_signal else "⚠️"
                print(f"  {status_icon} Policy={policy}: score={cb_score}, signals={cb_signals[-3:]}")
                # Validate expected scores
                expected = {"PENALTY": -25, "BLOCK": -100, "NEUTRAL": 0}
                if cb_score != expected[policy]:
                    print(f"     ❌ Expected score={expected[policy]} but got {cb_score}")
                else:
                    print(f"     ✅ Score matches expected value ({expected[policy]})")
            except Exception as policy_err:
                print(f"  ❌ Policy={policy} raised unexpected error: {policy_err}")

    # Restore env to default
    os.environ["MACRO_BLIND_POLICY"] = "PENALTY"

    print("=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
