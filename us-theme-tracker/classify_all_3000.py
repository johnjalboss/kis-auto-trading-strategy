import json
import sqlite3
import re
import datetime
import time
import concurrent.futures
import requests
from theme_engine import ThemeEngine, DB_PATH

def fetch_summary_for_ticker(ticker: str) -> dict:
    """
    Fetches the business summary using requests and HTML regex parsing.
    This bypasses Yahoo Finance API crumb/auth blocks entirely by fetching the public HTML page.
    """
    url = f"https://finance.yahoo.com/quote/{ticker}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        # Small delay to prevent network congestion
        time.sleep(0.05)
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            html = r.text
            match = re.search(r'class="description[^"]*"\s*>\s*<p[^>]*>(.*?)</p>', html)
            if match:
                summary = match.group(1).strip()
                # Remove any inline HTML tags (like <strong> or <span>)
                summary = re.sub(r'<[^>]*>', '', summary)
                return {
                    "ticker": ticker,
                    "summary": summary
                }
    except Exception as e:
        pass
    return {"ticker": ticker, "summary": None}

def main():
    print("====================================================")
    print("  Starting HTML Bulk Classification Engine (3,000+ Stocks)")
    print("====================================================")
    
    engine = ThemeEngine()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Fetch ALL tickers that don't have summaries yet
    cursor.execute("""
        SELECT ticker FROM stock_metadata 
        WHERE summary IS NULL OR summary = 'FETCH_FAILED'
    """)
    tickers_to_fetch = [row[0] for row in cursor.fetchall()]
    print(f"Found {len(tickers_to_fetch)} stocks needing profile summaries.")
    
    if tickers_to_fetch:
        batch_size = 150
        results = []
        
        print(f"Downloading summaries in batches of {batch_size} (6 threads)...")
        for i in range(0, len(tickers_to_fetch), batch_size):
            batch = tickers_to_fetch[i:i+batch_size]
            print(f"Fetching batch {i//batch_size + 1} ({len(batch)} tickers)...")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                future_to_ticker = {executor.submit(fetch_summary_for_ticker, t): t for t in batch}
                for future in concurrent.futures.as_completed(future_to_ticker):
                    res = future.result()
                    results.append(res)
            
            print("Batch finished. Sleeping for 2 seconds to allow connection cooling...")
            time.sleep(2)
            
        # Update database with fetched profiles
        print("Saving company profiles to database...")
        now = datetime.datetime.now().isoformat()
        records = []
        failed_tickers = []
        
        for r in results:
            t = r["ticker"]
            if r["summary"]:
                records.append((r["summary"], now, t))
            else:
                failed_tickers.append((now, t))
                
        if records:
            cursor.executemany("""
                UPDATE stock_metadata 
                SET summary = ?, last_updated = ?
                WHERE ticker = ?
            """, records)
            
        if failed_tickers:
            cursor.executemany("""
                UPDATE stock_metadata 
                SET summary = 'FETCH_FAILED', last_updated = ?
                WHERE ticker = ?
            """, failed_tickers)
            
        conn.commit()
        print(f"Saved {len(records)} summaries. Failed to fetch {len(failed_tickers)} summaries.")
        
    # 2. Run rule-based keyword match classification on all 3,000+ stocks
    print("Running rule-based & keyword mapping engine...")
    engine.themes_config = engine.load_themes_config()
    engine.run_rule_based_classification(limit=5000)
    
    # Check updated stats
    cursor.execute("SELECT COUNT(*) FROM stock_metadata WHERE theme_tags != ''")
    classified_count = cursor.fetchone()[0]
    print(f"Total stocks successfully classified: {classified_count} / 3000")
    
    # 3. Download price history for newly classified stocks
    cursor.execute("SELECT ticker FROM stock_metadata WHERE theme_tags != ''")
    classified_tickers = [row[0] for row in cursor.fetchall()]
    
    # Check if we already have daily data for them
    cursor.execute("SELECT DISTINCT ticker FROM stock_daily_data")
    has_prices = {row[0] for row in cursor.fetchall()}
    
    tickers_needing_prices = [t for t in classified_tickers if t not in has_prices]
    print(f"Found {len(tickers_needing_prices)} newly classified stocks needing price history.")
    
    if tickers_needing_prices:
        print(f"Downloading historical price & volume data for {len(tickers_needing_prices)} stocks...")
        engine.download_historical_data_batch(tickers_needing_prices)
        
    # 4. Calculate theme metrics and signals
    print("Recalculating theme metrics and signal validation states...")
    theme_metrics = engine.calculate_theme_metrics()
    print(f"Done! Calculated signals for {len(theme_metrics)} themes.")
    
    conn.close()
    engine.close()

if __name__ == "__main__":
    main()
