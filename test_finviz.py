import requests, sys

try:
    resp = requests.get(
        "https://finviz.com/quote.ashx?t=AAPL",
        headers={"User-Agent": "Mozilla/5.0 (compatible; trading-bot/2.0)"},
        timeout=8
    )
    print("Finviz status:", resp.status_code, "len:", len(resp.text))
    blocked = "blocked" in resp.text.lower() or "captcha" in resp.text.lower()
    if resp.status_code in [403, 429, 503] or blocked:
        print("BLOCKED by Finviz - Oracle VPS IP banned")
    else:
        print("OK - Finviz accessible from VPS")
        news_count = resp.text.count("news-link")
        print("News link count:", news_count)
except Exception as e:
    print("Finviz error:", type(e).__name__, str(e))
