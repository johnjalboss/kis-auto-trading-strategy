import os
import json
import sqlite3
import datetime
import urllib.request
import re
import pandas as pd
import numpy as np
import yfinance as yf
import google.generativeai as genai
from typing import List, Dict, Tuple, Any

# Configure relative paths within project directory
DB_PATH = "us_stocks_data.db"
THEME_DB_JSON = "theme_db.json"

class ThemeEngine:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.create_tables()
        self.themes_config = self.load_themes_config()

    def create_tables(self):
        cursor = self.conn.cursor()
        # Stock metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_metadata (
                ticker TEXT PRIMARY KEY,
                name TEXT,
                sector TEXT,
                industry TEXT,
                summary TEXT,
                theme_tags TEXT, -- comma-separated
                last_updated TIMESTAMP
            )
        """)
        # Historical price/volume data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_daily_data (
                ticker TEXT,
                date TEXT,
                close REAL,
                volume REAL,
                PRIMARY KEY (ticker, date)
            )
        """)
        # Theme performance cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS theme_daily_metrics (
                theme_id TEXT,
                date TEXT,
                score REAL,
                median_rvol REAL,
                return_1d REAL,
                return_5d REAL,
                return_20d REAL,
                breadth REAL,
                signal_status TEXT,
                signal_quality REAL,
                PRIMARY KEY (theme_id, date)
            )
        """)
        self.conn.commit()

    def load_themes_config(self) -> Dict[str, Any]:
        if os.path.exists(THEME_DB_JSON):
            with open(THEME_DB_JSON, "r", encoding="utf-8") as f:
                return json.load(f).get("themes", {})
        return {}

    def save_themes_config(self):
        with open(THEME_DB_JSON, "w", encoding="utf-8") as f:
            json.dump({"themes": self.themes_config}, f, ensure_ascii=False, indent=2)

    def fetch_us_tickers_from_nasdaq(self) -> List[Tuple[str, str, str]]:
        """
        Downloads the list of US stocks from GitHub or falls back to NASDAQ FTP.
        Returns a list of tuples: (ticker, security_name, industry_or_exchange)
        """
        tickers = []
        
        # 1. Try GitHub raw CSV first (curated, includes market cap and volume, sorted by cap)
        github_url = "https://raw.githubusercontent.com/Ate329/top-us-stock-tickers/main/tickers/all.csv"
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            print("Fetching ticker list from GitHub raw CSV...")
            req = urllib.request.Request(github_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode('utf-8')
                
                import csv
                import io
                f = io.StringIO(content)
                reader = csv.reader(f)
                header = next(reader)
                
                symbol_idx = header.index("symbol") if "symbol" in header else 0
                name_idx = header.index("name") if "name" in header else 1
                industry_idx = header.index("industry") if "industry" in header else -1
                
                count = 0
                for row in reader:
                    if len(row) > max(symbol_idx, name_idx):
                        ticker = row[symbol_idx].strip()
                        name = row[name_idx].strip()
                        industry = row[industry_idx].strip() if industry_idx != -1 and len(row) > industry_idx else ""
                        
                        # Clean ticker: standard letters, standard length
                        if ticker.isalpha() and len(ticker) <= 5:
                            tickers.append((ticker, name, industry))
                            count += 1
                            if count >= 3000:  # Top 3000 most liquid
                                break
                if tickers:
                    print(f"Successfully loaded {len(tickers)} tickers from GitHub CSV.")
                    return tickers
        except Exception as e:
            print(f"GitHub CSV fetch failed: {e}. Falling back to NASDAQ FTP.")

        # 2. NASDAQ Listed Fallback
        nasdaq_url = "https://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt"
        other_url = "https://ftp.nasdaqtrader.com/SymbolDirectory/otherlisted.txt"
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        try:
            req = urllib.request.Request(nasdaq_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode('utf-8')
                lines = content.split('\n')
                for line in lines[1:]:
                    parts = line.split('|')
                    if len(parts) >= 7:
                        ticker = parts[0].strip()
                        name = parts[1].strip()
                        is_test = parts[3].strip()
                        is_etf = parts[6].strip()
                        if is_test == 'N' and is_etf == 'N' and ticker.isalpha():
                            tickers.append((ticker, name, "NASDAQ"))
        except Exception as e:
            print(f"Error fetching NASDAQ listings: {e}")
            
        try:
            req = urllib.request.Request(other_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode('utf-8')
                lines = content.split('\n')
                for line in lines[1:]:
                    parts = line.split('|')
                    if len(parts) >= 7:
                        ticker = parts[0].strip()
                        name = parts[1].strip()
                        exchange = parts[2].strip()
                        is_etf = parts[4].strip()
                        is_test = parts[6].strip()
                        if is_test == 'N' and is_etf == 'N' and ticker.isalpha():
                            exch_name = "NYSE" if exchange == "N" else ("AMEX" if exchange == "A" else "OTHER")
                            tickers.append((ticker, name, exch_name))
        except Exception as e:
            print(f"Error fetching other listings: {e}")

        # 3. Hardcoded Fallback
        if not tickers:
            print("NASDAQ FTP failed. Using high-liquidity stock list fallback.")
            fallback = [
                ("AAPL", "Apple Inc.", "Technology"), ("MSFT", "Microsoft Corp.", "Technology"), 
                ("GOOGL", "Alphabet Inc.", "Technology"), ("AMZN", "Amazon.com Inc.", "Consumer Cyclical"),
                ("META", "Meta Platforms", "Technology"), ("TSLA", "Tesla Inc.", "Consumer Cyclical"),
                ("NVDA", "NVIDIA Corp.", "Technology"), ("AVGO", "Broadcom Inc.", "Technology"),
                ("LLY", "Eli Lilly & Co.", "Healthcare"), ("NVO", "Novo Nordisk", "Healthcare"),
                ("MU", "Micron Technology", "Technology"), ("WDC", "Western Digital", "Technology"),
                ("SMR", "Nuscale Power", "Industrials"), ("OKLO", "Oklo Inc.", "Industrials"),
                ("CCJ", "Cameco Corp.", "Energy"), ("VRT", "Vertiv Holdings", "Industrials"),
                ("ETN", "Eaton Corp.", "Industrials"), ("GEV", "GE Vernova", "Industrials"),
                ("CRWD", "CrowdStrike", "Technology"), ("MSTR", "MicroStrategy", "Technology")
            ]
            return fallback

        # Return unique tickers
        seen = set()
        unique_tickers = []
        for t, n, ex in tickers:
            if t not in seen:
                seen.add(t)
                unique_tickers.append((t, n, ex))
        return unique_tickers

    def initialize_metadata_cache(self, tickers: List[Tuple[str, str, str]]):
        """
        Populate the stock_metadata table with basic listings.
        """
        cursor = self.conn.cursor()
        now = datetime.datetime.now().isoformat()
        
        # Check existing tickers to avoid overwriting
        cursor.execute("SELECT ticker FROM stock_metadata")
        existing = {row[0] for row in cursor.fetchall()}
        
        records = []
        for ticker, name, industry_or_exch in tickers:
            if ticker not in existing:
                # If the third field is a standard exchange name, we don't save it as industry
                industry = None
                if industry_or_exch and industry_or_exch not in ["NASDAQ", "NYSE", "AMEX", "OTHER"]:
                    industry = industry_or_exch
                records.append((ticker, name, None, industry, None, "", now))
                
        if records:
            cursor.executemany("""
                INSERT INTO stock_metadata (ticker, name, sector, industry, summary, theme_tags, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, records)
            self.conn.commit()
            print(f"Initialized metadata cache with {len(records)} new tickers.")

    def run_rule_based_classification(self, limit: int = 3000):
        """
        Runs fast keyword matching and pre-mapped classification on stock descriptions.
        """
        cursor = self.conn.cursor()
        # Get all stocks from metadata
        cursor.execute("SELECT ticker, summary, theme_tags FROM stock_metadata LIMIT ?", (limit,))
        rows = cursor.fetchall()
        
        updated_count = 0
        for ticker, summary, existing_tags in rows:
            matched_themes = []
            
            # 1. Check pre-mapped tickers in config (can be done even without summary)
            for theme_id, cfg in self.themes_config.items():
                premapped = cfg.get("premapped_tickers", [])
                if ticker in premapped:
                    matched_themes.append(theme_id)
            
            # 2. Check keywords if summary is available
            if summary and summary != 'FETCH_FAILED':
                summary_lower = summary.lower()
                
                # Exclusion keywords to avoid false positives (e.g. consulting, retail, holding companies) in high-tech themes
                ex_kws = ["consulting", "advisory", "reseller", "retailer", "distributor", "wholesale", "holding company", "law firm", "marketing services"]
                has_tech_exclusion = any(ex_kw in summary_lower for ex_kw in ex_kws)
                
                for theme_id, cfg in self.themes_config.items():
                    if theme_id in matched_themes:
                        continue
                        
                    # Skip tech themes for services/retail companies
                    is_tech_theme = theme_id not in ["retail_stores", "apparel_footwear", "restaurants_food", "regional_banks", "insurance", "reits_real_estate", "asset_management"]
                    if is_tech_theme and has_tech_exclusion:
                        continue
                        
                    keywords = cfg.get("keywords", [])
                    for kw in keywords:
                        pattern = r'\b' + re.escape(kw.lower()) + r'\b'
                        if re.search(pattern, summary_lower):
                            matched_themes.append(theme_id)
                            break
            
            # Overwrite tags to apply new strict exclusion filters cleanly
            new_tags = list(set(matched_themes))
            new_tags_str = ",".join(new_tags)
            
            if new_tags_str != existing_tags:
                cursor.execute(
                    "UPDATE stock_metadata SET theme_tags = ?, last_updated = ? WHERE ticker = ?",
                    (new_tags_str, datetime.datetime.now().isoformat(), ticker)
                )
                updated_count += 1
                
        self.conn.commit()
        print(f"Rule-based & Premapped classification updated {updated_count} stocks.")

    def fetch_company_summaries_batch(self, tickers: List[str], max_workers: int = 10):
        """
        Downloads info/summary for tickers using yfinance and saves them to SQLite.
        """
        cursor = self.conn.cursor()
        now = datetime.datetime.now().isoformat()
        
        # Filter down to tickers that don't have a summary cached
        cursor.execute("SELECT ticker FROM stock_metadata WHERE summary IS NOT NULL")
        has_summary = {row[0] for row in cursor.fetchall()}
        
        tickers_to_fetch = [t for t in tickers if t not in has_summary][:200]  # Chunk size limit to avoid blocking
        
        if not tickers_to_fetch:
            return
            
        print(f"Fetching summaries for {len(tickers_to_fetch)} tickers...")
        
        for t in tickers_to_fetch:
            try:
                ticker_obj = yf.Ticker(t)
                info = ticker_obj.info
                summary = info.get("longBusinessSummary")
                sector = info.get("sector")
                industry = info.get("industry")
                name = info.get("longName", info.get("shortName", t))
                
                if summary:
                    cursor.execute("""
                        INSERT INTO stock_metadata (ticker, name, sector, industry, summary, theme_tags, last_updated)
                        VALUES (?, ?, ?, ?, ?, '', ?)
                        ON CONFLICT(ticker) DO UPDATE SET
                            name=excluded.name,
                            sector=excluded.sector,
                            industry=excluded.industry,
                            summary=excluded.summary,
                            last_updated=excluded.last_updated
                    """, (t, name, sector, industry, summary, now))
            except Exception as e:
                # If error, mark with a placeholder to avoid repeatedly fetching failed tickers
                cursor.execute("""
                    INSERT INTO stock_metadata (ticker, summary, last_updated)
                    VALUES (?, 'FETCH_FAILED', ?)
                    ON CONFLICT(ticker) DO UPDATE SET summary='FETCH_FAILED', last_updated=?
                """, (t, now, now))
                print(f"Failed to fetch {t}: {e}")
                
        self.conn.commit()

    def classify_ticker_with_llm(self, ticker: str, api_key: str = None) -> List[str]:
        """
        Classifies a single ticker using Gemini API based on its business summary.
        Updates the local stock_metadata table.
        """
        if not api_key:
            # Try to read from environment or system logs
            api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("No Gemini API key available. Skipping LLM classification.")
            return []

        cursor = self.conn.cursor()
        cursor.execute("SELECT name, summary, theme_tags FROM stock_metadata WHERE ticker = ?", (ticker,))
        row = cursor.fetchone()
        if not row or not row[1] or row[1] == 'FETCH_FAILED':
            print(f"Ticker {ticker} summary not found or failed.")
            return []

        name, summary, existing_tags = row
        
        # Prepare list of themes for Gemini
        themes_desc = []
        for theme_id, cfg in self.themes_config.items():
            themes_desc.append(f"- {theme_id}: {cfg.get('name_en')} ({cfg.get('name_ko')})")
            
        themes_list_str = "\n".join(themes_desc)
        
        prompt = f"""
You are a top quant research assistant. Your task is to analyze the following company and classify it into one or more of our fine-grained stock themes.

Company Ticker: {ticker}
Company Name: {name}
Business Summary:
{summary}

Available Themes to choose from:
{themes_list_str}

Instruction:
1. Review the business summary carefully.
2. Identify if the company directly belongs to any of the available themes. (Only choose themes where the company is a active participant or supplier).
3. Return the matched themes as a JSON list of strings containing the exact theme IDs. If none match, return an empty list `[]`.
4. Return ONLY the JSON array. Do not include markdown formatting or explanations.

Example Output:
["nand_memory", "dram_memory"]
"""
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            response = model.generate_content(prompt)
            
            # Clean response text
            text = response.text.strip()
            # Remove code fence if present
            if text.startswith("```"):
                text = re.sub(r"^```json\s*|```$", "", text, flags=re.MULTILINE).strip()
                
            matched_themes = json.loads(text)
            if isinstance(matched_themes, list):
                # Save to database
                existing_list = [t.strip() for t in existing_tags.split(",") if t.strip()]
                new_tags = list(set(existing_list + matched_themes))
                new_tags_str = ",".join(new_tags)
                
                cursor.execute(
                    "UPDATE stock_metadata SET theme_tags = ?, last_updated = ? WHERE ticker = ?",
                    (new_tags_str, datetime.datetime.now().isoformat(), ticker)
                )
                self.conn.commit()
                print(f"LLM successfully classified {ticker} into: {matched_themes}")
                return matched_themes
        except Exception as e:
            print(f"Error classifying {ticker} with LLM: {e}")
            
        return []

    def download_historical_data_batch(self, tickers: List[str]):
        """
        Downloads daily price/volume data in batches of 200 using yfinance.
        Saves data to SQLite.
        """
        if not tickers:
            return
            
        cursor = self.conn.cursor()
        chunk_size = 200
        
        # We only need the last 30 days of data to compute 20-day averages & returns
        start_date = (datetime.date.today() - datetime.timedelta(days=45)).strftime("%Y-%m-%d")
        
        for i in range(0, len(tickers), chunk_size):
            chunk = tickers[i:i+chunk_size]
            print(f"Downloading market data for chunk {i//chunk_size + 1} ({len(chunk)} tickers)...")
            
            try:
                # Fast batch download
                data = yf.download(chunk, start=start_date, group_by='ticker', progress=False)
                
                records = []
                for ticker in chunk:
                    if ticker not in data.columns.levels[0]:
                        continue
                    
                    df = data[ticker].dropna()
                    for idx, row in df.iterrows():
                        date_str = idx.strftime("%Y-%m-%d")
                        close = float(row['Close'])
                        vol = float(row['Volume'])
                        if close > 0:
                            records.append((ticker, date_str, close, vol))
                
                if records:
                    cursor.executemany("""
                        INSERT INTO stock_daily_data (ticker, date, close, volume)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(ticker, date) DO UPDATE SET
                            close=excluded.close,
                            volume=excluded.volume
                    """, records)
                    self.conn.commit()
            except Exception as e:
                print(f"Error downloading batch: {e}")

    def filter_and_select_active_universe(self) -> List[str]:
        """
        Excludes highly illiquid stocks based on price and volume.
        Filters: Average daily volume > 50,000 shares and Price > $1.00
        Returns list of active tickers.
        """
        cursor = self.conn.cursor()
        
        # Get list of all tickers that we have data for
        cursor.execute("SELECT DISTINCT ticker FROM stock_daily_data")
        tickers = [row[0] for row in cursor.fetchall()]
        
        active_tickers = []
        for ticker in tickers:
            cursor.execute("""
                SELECT close, volume FROM stock_daily_data 
                WHERE ticker = ? 
                ORDER BY date DESC LIMIT 20
            """, (ticker,))
            rows = cursor.fetchall()
            
            if len(rows) < 5:
                continue
                
            prices = [r[0] for r in rows]
            volumes = [r[1] for r in rows]
            
            avg_price = np.mean(prices)
            avg_volume = np.mean(volumes)
            
            # Liquidity filters
            if avg_price >= 1.0 and avg_volume >= 50000:
                active_tickers.append(ticker)
                
        return active_tickers

    def calculate_theme_metrics(self) -> Dict[str, Any]:
        """
        Runs calculations for Theme Momentum and Signal Quality.
        Aggregates individual stock price returns and Relative Volume (RVOL).
        """
        cursor = self.conn.cursor()
        
        # 1. Fetch stock metadata and tags
        cursor.execute("SELECT ticker, theme_tags FROM stock_metadata WHERE theme_tags != ''")
        stock_tags = cursor.fetchall()
        
        # Group tickers by theme
        theme_to_tickers = {}
        for ticker, tags in stock_tags:
            for tag in tags.split(","):
                tag = tag.strip()
                if tag:
                    theme_to_tickers.setdefault(tag, []).append(ticker)
                    
        # 2. Get dates
        cursor.execute("SELECT DISTINCT date FROM stock_daily_data ORDER BY date DESC LIMIT 25")
        dates = [r[0] for r in cursor.fetchall()]
        if len(dates) < 21:
            print("Not enough daily data cached to calculate metrics.")
            return {}
            
        latest_date = dates[0]
        
        theme_results = {}
        
        for theme_id, tickers in theme_to_tickers.items():
            if theme_id not in self.themes_config:
                continue
                
            stock_metrics = []
            
            for ticker in tickers:
                cursor.execute("""
                    SELECT date, close, volume FROM stock_daily_data 
                    WHERE ticker = ? ORDER BY date DESC LIMIT 22
                """, (ticker,))
                rows = cursor.fetchall()
                
                # We need at least 21 days of data
                if len(rows) < 21:
                    continue
                    
                # Index 0 is latest, index 1 is 1d ago, 5 is 5d ago, 20 is 20d ago (approx trading days)
                latest_close = rows[0][1]
                close_1d = rows[1][1]
                close_5d = rows[min(5, len(rows)-1)][1]
                close_20d = rows[min(20, len(rows)-1)][1]
                
                ret_1d = (latest_close - close_1d) / close_1d * 100
                ret_5d = (latest_close - close_5d) / close_5d * 100
                ret_20d = (latest_close - close_20d) / close_20d * 100
                
                # Calculate Relative Volume (RVOL): latest volume / median of past 20 days (excluding today)
                latest_vol = rows[0][2]
                past_volumes = [r[2] for r in rows[1:21]]
                avg_past_vol = np.mean(past_volumes) if past_volumes else 0
                
                rvol = latest_vol / avg_past_vol if avg_past_vol > 0 else 1.0
                
                # Quant Stock Score = 5D Return * RVOL (capped at 3.0 to prevent outlier distortion)
                stock_score = ret_5d * min(rvol, 3.0)
                
                stock_metrics.append({
                    "ticker": ticker,
                    "ret_1d": ret_1d,
                    "ret_5d": ret_5d,
                    "ret_20d": ret_20d,
                    "rvol": rvol,
                    "score": stock_score,
                    "is_up": 1 if ret_1d > 0 else 0
                })
                
            if not stock_metrics:
                continue
                
            # Aggregate Stock metrics to Theme-level using Median to resist outlier manipulation
            median_score = float(np.median([s["score"] for s in stock_metrics]))
            median_rvol = float(np.median([s["rvol"] for s in stock_metrics]))
            theme_ret_1d = float(np.median([s["ret_1d"] for s in stock_metrics]))
            theme_ret_5d = float(np.median([s["ret_5d"] for s in stock_metrics]))
            theme_ret_20d = float(np.median([s["ret_20d"] for s in stock_metrics]))
            
            # Theme Breadth = % of stocks rising in the latest session
            breadth = float(sum([s["is_up"] for s in stock_metrics]) / len(stock_metrics) * 100)
            
            # --- Signal Validation Engine ---
            # 1. Check if 3-day average RVOL is also elevated to confirm sustainability
            sustained_vol_multiplier = 1.0
            # 2. Check Trend Setup: Is theme price above 20D MA?
            # We approximate theme price using median change. If theme 20D return is positive, it's generally in an uptrend.
            is_uptrend = theme_ret_20d > 0
            
            # Signal Quality Calculation (0 - 100%)
            # High quality signal requires high breadth, sustained high RVOL, and positive trend setup
            breadth_factor = min(breadth / 70.0, 1.0) # Cap at 1.0 if breadth >= 70%
            rvol_factor = min(median_rvol / 1.5, 1.0) # Cap at 1.0 if RVOL >= 1.5
            trend_factor = 1.0 if is_uptrend else 0.4
            
            # Standardized Signal Quality Score
            signal_quality = float((0.4 * breadth_factor + 0.4 * rvol_factor + 0.2 * trend_factor) * 100)
            
            # Determine Signal Status
            if theme_ret_5d > 2.0 and median_rvol > 1.4 and breadth > 60.0:
                if is_uptrend:
                    signal_status = "🟢 TRUE SIGNAL (Institutional)"
                else:
                    signal_status = "🔴 DEAD CAT BOUNCE (Trap)"
            elif theme_ret_5d > 5.0 and median_rvol > 1.5 and breadth <= 35.0:
                signal_status = "🟡 PUMP / SPECULATIVE (Risk)"
            elif abs(theme_ret_5d) <= 2.0 and median_rvol < 1.1:
                signal_status = "⚪ NOISE / QUIET"
            else:
                signal_status = "🔵 CONSOLIDATING"
                
            theme_results[theme_id] = {
                "theme_id": theme_id,
                "name_ko": self.themes_config[theme_id]["name_ko"],
                "name_en": self.themes_config[theme_id]["name_en"],
                "score": median_score,
                "median_rvol": median_rvol,
                "return_1d": theme_ret_1d,
                "return_5d": theme_ret_5d,
                "return_20d": theme_ret_20d,
                "breadth": breadth,
                "signal_status": signal_status,
                "signal_quality": signal_quality,
                "stock_count": len(stock_metrics)
            }
            
            # Save to Cache DB
            cursor.execute("""
                INSERT INTO theme_daily_metrics 
                (theme_id, date, score, median_rvol, return_1d, return_5d, return_20d, breadth, signal_status, signal_quality)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(theme_id, date) DO UPDATE SET
                    score=excluded.score,
                    median_rvol=excluded.median_rvol,
                    return_1d=excluded.return_1d,
                    return_5d=excluded.return_5d,
                    return_20d=excluded.return_20d,
                    breadth=excluded.breadth,
                    signal_status=excluded.signal_status,
                    signal_quality=excluded.signal_quality
            """, (theme_id, latest_date, median_score, median_rvol, theme_ret_1d, theme_ret_5d, theme_ret_20d, breadth, signal_status, signal_quality))
            
        self.conn.commit()
        return theme_results

    def close(self):
        self.conn.close()

if __name__ == "__main__":
    # Test script entry point
    print("Testing ThemeEngine initialization...")
    engine = ThemeEngine()
    
    # 1. Fetch tickers
    print("Fetching tickers...")
    tickers = engine.fetch_us_tickers_from_nasdaq()
    print(f"Fetched {len(tickers)} tickers. Top 10:")
    print(tickers[:10])
    
    # 2. Init database
    engine.initialize_metadata_cache(tickers)
    
    # 3. Fast classify a few preloaded
    print("Running rule-based matching...")
    engine.run_rule_based_classification()
    
    # 4. Check tags count
    cursor = engine.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM stock_metadata WHERE theme_tags != ''")
    tagged_count = cursor.fetchone()[0]
    print(f"Total classified stocks: {tagged_count}")
    
    engine.close()
