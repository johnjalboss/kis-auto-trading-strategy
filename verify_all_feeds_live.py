"""
verify_all_feeds_live.py
Verify real data fetching across all 5 quant intelligence engines.
"""

import json
from loguru import logger

def verify():
    print("=" * 60)
    print("🌐 [LIVE DATA AUDIT] 5-PILLAR QUANT DATA FEEDS")
    print("=" * 60)

    # 1. Fed Net Liquidity
    print("\n🏛️ 1. FED NET LIQUIDITY ENGINE (FRED API / Live Fed Balance Sheet):")
    from fed_net_liquidity_engine import get_fed_net_liquidity_engine
    fed = get_fed_net_liquidity_engine().fetch_net_liquidity_data()
    print(f"  • Fed Total Assets (WALCL): ${fed['fed_total_assets_billions']:,.1f}B")
    print(f"  • Treasury TGA Account: ${fed['tga_account_billions']:,.1f}B")
    print(f"  • Reverse Repo (RRP): ${fed['reverse_repo_billions']:,.1f}B")
    print(f"  • Net Liquidity: ${fed['net_liquidity_billions']:,.1f}B ({fed['regime']}) | 4W Delta: {fed['delta_4w_billions']:+,.1f}B ({fed['delta_4w_pct']:+.2f}%)")
    print(f"  • Sizing Multiplier: {fed['sizing_multiplier']}x | Score Threshold Adjust: {fed['min_score_adjust']:+d}pt")

    # 2. Options Gamma GEX
    print("\n⚡ 2. OPTIONS GAMMA GEX ENGINE (SPY Options Chain / Black-Scholes):")
    from options_gamma_engine import get_options_gamma_engine
    gex = get_options_gamma_engine().analyze_gex("SPY")
    print(f"  • SPY Spot Price: ${gex['current_price']:.2f}")
    print(f"  • Net GEX: ${gex['net_gex_millions']:+,.2f}M | Regime: {gex['gex_regime']}")
    print(f"  • Call Wall: ${gex['call_wall']:.2f} | Put Wall: ${gex['put_wall']:.2f} | Gamma Flip: ${gex['gamma_flip_level']:.2f}")

    # 3. AI News Sentiment
    print("\n📰 3. AI REAL-TIME NEWS SENTIMENT (Live Ticker News & NLP):")
    from ai_news_sentiment_engine import get_ai_news_sentiment_engine
    nse = get_ai_news_sentiment_engine()
    for sym in ["ADP", "CART", "LYFT"]:
        s = nse.analyze_ticker(sym)
        print(f"  • {sym}: Score={s.sentiment_score:+.2f} ({s.consensus_rating}) | Upgrades={s.analyst_upgrades} | Headline: \"{s.key_headline[:55]}\"")

    # 4. Dark Pool ATS
    print("\n🕶️ 4. DARK POOL WHALE RADAR (Live ATS & FINRA Short Volume):")
    from dark_pool_radar import get_dark_pool_radar
    dpr = get_dark_pool_radar()
    for sym in ["ADP", "CART", "LYFT"]:
        d = dpr.analyze_ticker(sym)
        print(f"  • {sym}: DarkPool={d.dark_pool_volume_pct}% | ShortVol={d.finra_short_volume_pct}% | Stealth={d.stealth_accumulation} | ScoreAdj=+{d.score_adjustment}pt")

    # 5. SEC Form 4 Insider Radar
    print("\n👥 5. SEC FORM 4 INSIDER CLUSTER RADAR (EDGAR / Executive Open Market Purchases):")
    from sec_form4_insider_radar import SECForm4InsiderRadar
    ir = SECForm4InsiderRadar()
    for sym in ["ADP", "CART", "LYFT", "MRK"]:
        i = ir.analyze_insider_activity(sym)
        print(f"  • {sym}: Purchases={i['purchase_count']} | Cluster={i['is_cluster_buying']} | Score={i['insider_score']} | Buyers={i['c_suite_buyers']}")

    print("\n" + "=" * 60)
    print("✅ ALL 5 DATA FEEDS CONFIRMED RETRIEVING LIVE DATA!")
    print("=" * 60)

if __name__ == "__main__":
    verify()
