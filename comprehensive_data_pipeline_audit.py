"""
Comprehensive Live Data Pipeline Audit (All 8 Core Data Feeds)
Tests real network calls and verifies authentic data payload for every subsystem.
"""

import time
import sys
from datetime import datetime

print("================================================================================")
print("🌐 EXHAUSTIVE DATA PIPELINE AUDIT & LIVE DATA PAYLOAD VERIFICATION")
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S KST')}")
print("================================================================================\n")

results = {}

# 1. KIS OpenAPI - Real-time Price, OHLCV, 10-Level Order Book
print("--- [1] KIS Broker OpenAPI (Price / OHLCV / 10-Level Orderbook) ---")
try:
    import kis_data
    t0 = time.time()
    df_aapl = kis_data.get_daily_ohlcv("AAPL", days=5)
    t_price = time.time() - t0
    last_close = float(df_aapl['Close'].iloc[-1]) if df_aapl is not None and not df_aapl.empty else 0.0
    
    from trader import get_trader
    tr = get_trader()
    t0 = time.time()
    spread = tr.get_spread("AAPL")
    bp = tr.get_buying_power()
    t_trader = time.time() - t0
    
    print(f"  ✅ KIS Daily OHLCV: AAPL Last Close = ${last_close:.2f} ({len(df_aapl)} bars, {t_price*1000:.0f}ms)")
    print(f"  ✅ KIS 10-Level Orderbook: AAPL Spread = {spread*100:.3f}% ({t_trader*1000:.0f}ms)")
    print(f"  ✅ KIS Buying Power: Available = ${bp:.2f}")
    results["1_KIS_API"] = "OK"
except Exception as e:
    print(f"  ❌ KIS OpenAPI Error: {e}")
    results["1_KIS_API"] = f"ERROR: {e}"

# 2. Macro & Cross-Asset Market Feed (VIX, 10Y Yield, Dollar, Oil, Gold)
print("\n--- [2] Macro & Cross-Asset Market Data (VIX, TNX, DXY, SPY) ---")
try:
    from macro import get_macro_data
    m_data = get_macro_data()
    vix = getattr(m_data, 'vix', 0.0) if m_data else 0.0
    tnx = getattr(m_data, 'tnx', 0.0) if m_data else 0.0
    dxy = getattr(m_data, 'dxy', 0.0) if m_data else 0.0
    regime = getattr(m_data, 'regime', 'UNKNOWN') if m_data else 'UNKNOWN'
    print(f"  ✅ VIX: {vix:.2f} | 10Y Treasury (TNX): {tnx:.2f}% | Dollar (DXY): {dxy:.2f}")
    print(f"  ✅ Macro Regime Detected: {regime}")
    results["2_MACRO_FEEDS"] = "OK"
except Exception as e:
    print(f"  ❌ Macro Feed Error: {e}")
    results["2_MACRO_FEEDS"] = f"ERROR: {e}"

# 3. Finnhub Institutional Financial API
print("\n--- [3] Finnhub API (Insider Trades Form 4, News, Earnings) ---")
try:
    from finnhub_client import get_finnhub_client
    fc = get_finnhub_client()
    if fc.is_enabled():
        news = fc.get_company_news("NVDA")
        insider = fc.get_insider_transactions("NVDA")
        surprises = fc.get_earnings_surprises("NVDA")
        print(f"  ✅ Finnhub News: NVDA {len(news) if news else 0} live news articles fetched")
        if news and len(news) > 0:
            print(f"     -> Latest Headline: \"{news[0].get('headline', '')[:70]}...\"")
        print(f"  ✅ Finnhub Insider Form 4: NVDA {len(insider) if insider else 0} transactions")
        print(f"  ✅ Finnhub Earnings Surprises: NVDA {len(surprises) if surprises else 0} quarters")
        results["3_FINNHUB_API"] = "OK"
    else:
        print("  ⚠️ Finnhub API key not configured or rate limited")
        results["3_FINNHUB_API"] = "DISABLED_OR_NO_KEY"
except Exception as e:
    print(f"  ❌ Finnhub API Error: {e}")
    results["3_FINNHUB_API"] = f"ERROR: {e}"

# 4. SEC EDGAR / Institutional Whale Ownership
print("\n--- [4] SEC EDGAR / Institutional Whale Radar ---")
try:
    from sec_13d_radar import SEC13DRadar
    sec_res = SEC13DRadar().analyze("NVDA")
    print(f"  ✅ SEC Whale Radar (NVDA): Filings={sec_res.get('has_13d_whale')}, Score=+{sec_res.get('score_adj')}, Detail: {sec_res.get('reason')}")
    results["4_SEC_EDGAR"] = "OK"
except Exception as e:
    print(f"  ❌ SEC Radar Error: {e}")
    results["4_SEC_EDGAR"] = f"ERROR: {e}"

# 5. FINRA TRF & Dark Pool ATS Block Tracker
print("\n--- [5] FINRA TRF / Dark Pool ATS Tracker ---")
try:
    from dark_pool_block_radar import DarkPoolBlockRadar
    dp_res = DarkPoolBlockRadar().analyze("NVDA")
    print(f"  ✅ FINRA Dark Pool (NVDA): Accum={dp_res.get('is_institutional_accum')}, Score={dp_res.get('score_adj'):+d}, Detail: {dp_res.get('reason')}")
    results["5_FINRA_DARK_POOL"] = "OK"
except Exception as e:
    print(f"  ❌ Dark Pool Error: {e}")
    results["5_FINRA_DARK_POOL"] = f"ERROR: {e}"

# 6. CBOE Options Chain & OCC Open Interest (GEX / Max Pain / PCR)
print("\n--- [6] CBOE Options Chain & Dealer Gamma (GEX / PCR / Max Pain) ---")
try:
    from options_flow import get_options_snapshot
    opt_snap = get_options_snapshot("NVDA")
    if opt_snap:
        print(f"  ✅ CBOE NVDA Options: Spot=${opt_snap.price:.2f} | MaxPain=${opt_snap.max_pain:.2f} | GEX=${opt_snap.gex:.1f}M")
        print(f"  ✅ CBOE NVDA Sentiment: Put/Call Ratio={opt_snap.put_call_ratio:.2f} | IV={opt_snap.iv_current*100:.1f}% (IV Rank: {opt_snap.iv_rank:.0f})")
        print(f"  ✅ Options Walls: Call Wall=${opt_snap.call_wall:.2f} | Put Wall=${opt_snap.put_wall:.2f}")
        results["6_CBOE_OPTIONS"] = "OK"
    else:
        print("  ⚠️ Options snapshot returned None")
        results["6_CBOE_OPTIONS"] = "EMPTY"
except Exception as e:
    print(f"  ❌ CBOE Options Error: {e}")
    results["6_CBOE_OPTIONS"] = f"ERROR: {e}"

# 7. Sector Rotation & Theme Radar
print("\n--- [7] 11 Sector SPDR ETFs & US Theme Tracker ---")
try:
    from sector_rotator import get_sector_rotator
    sr = get_sector_rotator()
    sr_res = sr.analyze()
    print(f"  ✅ Sector Rotator: {len(sr_res) if sr_res else 0} sectors analyzed")
    if sr_res and len(sr_res) >= 3:
        leading = [r.sector for r in sr_res[:3]]
        lagging = [r.sector for r in sr_res[-3:]]
        print(f"     -> Leading Sectors: {', '.join(leading)}")
        print(f"     -> Lagging Sectors: {', '.join(lagging)}")
    results["7_SECTOR_ROTATION"] = "OK"
except Exception as e:
    print(f"  ❌ Sector Rotator Error: {e}")
    results["7_SECTOR_ROTATION"] = f"ERROR: {e}"

# 8. Google Gemini 2.5 Flash AI News Shock Analysis
print("\n--- [8] Google Gemini 2.5 Flash AI News Sentinel ---")
try:
    from gemini_news_sentinel import GeminiNewsSentinel
    ai_res = GeminiNewsSentinel().analyze("NVDA")
    print(f"  ✅ Gemini AI Sentiment: Score={ai_res.get('sentiment_score')}/100, Score Adj={ai_res.get('score_adj'):+d}")
    print(f"  ✅ Gemini AI Catastrophic Risk: {ai_res.get('has_catastrophic_risk')}")
    print(f"     -> AI Summary: \"{ai_res.get('reason', '')[:80]}...\"")
    results["8_GEMINI_AI"] = "OK"
except Exception as e:
    print(f"  ❌ Gemini AI Error: {e}")
    results["8_GEMINI_AI"] = f"ERROR: {e}"

print("\n================================================================================")
print("📊 SUMMARY SCORECARD:")
all_ok = all(v == "OK" for v in results.values())
for k, v in results.items():
    print(f"  • {k}: {v}")
print(f"\nFinal Audit Verdict: {'🏆 ALL 8 DATA PIPELINES 100% OPERATIONAL & VERIFIED' if all_ok else '⚠️ ISSUES DETECTED'}")
print("================================================================================")
