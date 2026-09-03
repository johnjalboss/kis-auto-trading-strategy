import os
import sys
from dotenv import load_dotenv
from loguru import logger

# Reconfigure stdout to handle UTF-8 safely
sys.stdout.reconfigure(encoding='utf-8')

# Ensure we load environment variables
load_dotenv()

# Setup test log format
logger.remove()
logger.add(sys.stderr, level="DEBUG")

from finnhub_client import get_finnhub_client
from news_analyzer import get_news_analyzer
from insider_tracker import get_insider_tracker
from earnings_analyzer import get_earnings_analyzer

def test_integration():
    print("=" * 60)
    print("FINNHUB API FALLBACK SYSTEM: INTEGRATION TEST")
    print("=" * 60)
    
    client = get_finnhub_client()
    key = os.getenv("FINNHUB_API_KEY", "")
    
    if not key:
        print("⚠️  WARNING: FINNHUB_API_KEY is not set in your .env file!")
        print("To fully activate news/insider/earnings scans on Oracle VPS:")
        print("1. Go to https://finnhub.io/ and register a free account.")
        print("2. Copy your API Key.")
        print("3. Add the following line to your .env file on both local & remote VPS:")
        print("   FINNHUB_API_KEY=your_copied_api_key_here")
        print("\nSkipping live API queries since key is missing.")
        print("=" * 60)
        return
        
    print(f"✅ Finnhub API Key found: {key[:4]}...{key[-4:] if len(key) > 8 else ''}")
    print("Running dry-runs for symbol 'AAPL'...")
    
    # 1. Test News Sentiment
    print("\n[1/3] Testing News Sentiment (Finnhub fallback)...")
    try:
        na = get_news_analyzer()
        res_news = na.analyze("AAPL")
        print(f"  News Count: {res_news.news_count}")
        print(f"  Overall Sentiment: {res_news.overall_sentiment} (Score: {res_news.sentiment_score:+.1f})")
        print(f"  Recommendation: {res_news.recommendation}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        
    # 2. Test Insider Tracker
    print("\n[2/3] Testing Insider & Institutional Tracker (Finnhub fallback)...")
    try:
        it = get_insider_tracker()
        res_insider = it.analyze("AAPL")
        print(f"  Insider Sentiment: {res_insider.insider_sentiment}")
        print(f"  90d Buys: {res_insider.insider_buys_90d} | Sells: {res_insider.insider_sells_90d}")
        print(f"  Net Value: ${res_insider.insider_net_value:,.2f}")
        print(f"  Signal: {res_insider.signal} (Score: {res_insider.ownership_score:+d})")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        
    # 3. Test Earnings Analyzer
    print("\n[3/3] Testing Earnings Analyzer (Finnhub fallback)...")
    try:
        ea = get_earnings_analyzer()
        res_earnings = ea.analyze("AAPL")
        print(f"  Last EPS Surprise: {res_earnings.last_eps_surprise:+.2f}%")
        print(f"  Beat Streak: {res_earnings.beat_streak}")
        print(f"  Signal: {res_earnings.signal} (Score: {res_earnings.earnings_score:+d})")
        print(f"  Days since last report: {res_earnings.days_since_earnings} days")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        
    print("=" * 60)
    print("INTEGRATION TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    test_integration()
