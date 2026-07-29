#!/usr/bin/env python3
"""
Post-deploy validation for all 4 fixes.
"""
import sys, os

def run_validation():
    os.chdir('/home/ubuntu/kis-auto-trading')
    sys.path.insert(0, '/home/ubuntu/kis-auto-trading')

    errors = []
    passed = []

    # ─── 1. news_analyzer: cache_ttl = 7200, Finviz source present ───────────────
    try:
        from news_analyzer import NewsAnalyzer
        na = NewsAnalyzer()
        assert na._cache_ttl == 7200, f"Expected 7200 but got {na._cache_ttl}"
        import inspect
        src = inspect.getsource(na._fetch_news)
        assert 'Finviz' in src or 'finviz' in src, "Finviz source not found in _fetch_news"
        assert 'Source 2' in src or 'finviz.com' in src, "Finviz RSS block missing"
        passed.append("news_analyzer: cache_ttl=7200, Finviz source present")
    except Exception as e:
        errors.append(f"news_analyzer: {e}")

    # ─── 2. kis_data: BRKB→BRK-B yfinance mapping ───────────────────────────────
    try:
        import kis_data
        src2 = open('/home/ubuntu/kis-auto-trading/kis_data.py').read()
        assert 'YF_SYMBOL_MAP' in src2, "YF_SYMBOL_MAP not found in kis_data.py"
        assert '"BRKB": "BRK-B"' in src2, "BRKB->BRK-B mapping missing"
        passed.append("kis_data: BRKB->BRK-B YF_SYMBOL_MAP present")
    except Exception as e:
        errors.append(f"kis_data: {e}")

    # ─── 3. remote_kis_data: same fix ────────────────────────────────────────────
    try:
        src3 = open('/home/ubuntu/kis-auto-trading/remote_kis_data.py').read()
        assert 'YF_SYMBOL_MAP' in src3, "YF_SYMBOL_MAP not found in remote_kis_data.py"
        assert '"BRKB": "BRK-B"' in src3, "BRKB->BRK-B mapping missing"
        passed.append("remote_kis_data: BRKB->BRK-B YF_SYMBOL_MAP present")
    except Exception as e:
        errors.append(f"remote_kis_data: {e}")

    # ─── 4. fred_macro: VIXCLS + T10Y3M warmup present ──────────────────────────
    try:
        src4 = open('/home/ubuntu/kis-auto-trading/fred_macro.py').read()
        assert 'fetch_series_df("VIXCLS"' in src4 or "fetch_series_df('VIXCLS'" in src4, \
            "VIXCLS warmup not found"
        assert 'fetch_series_df("T10Y3M"' in src4 or "fetch_series_df('T10Y3M'" in src4, \
            "T10Y3M warmup not found"
        passed.append("fred_macro: VIXCLS + T10Y3M cache warmup present")
    except Exception as e:
        errors.append(f"fred_macro: {e}")

    # ─── 5. universe: BRK-B present, no duplicate BRKB in SP500_STATIC ──────────
    try:
        src5 = open('/home/ubuntu/kis-auto-trading/universe.py').read()
        # SP500_STATIC should have BRK-B not raw BRKB in the main list
        assert '"BRK-B"' in src5, "BRK-B not found in universe.py"
        passed.append("universe: BRK-B present in static list")
    except Exception as e:
        errors.append(f"universe: {e}")

    # ─── 6. Live Finviz fetch test (network) ─────────────────────────────────────
    try:
        import requests
        resp = requests.get(
            "https://finviz.com/quote.ashx?t=AAPL",
            headers={"User-Agent": "Mozilla/5.0 (compatible; trading-bot/2.0)"},
            timeout=10
        )
        ok = resp.status_code == 200
        if ok:
            # Check if any news-like text is present
            passed.append(f"Finviz live fetch: HTTP {resp.status_code}, content_len={len(resp.text)}")
        else:
            errors.append(f"Finviz live fetch: HTTP {resp.status_code}")
    except Exception as e:
        errors.append(f"Finviz live fetch failed: {e}")

    # ─── Summary ─────────────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("VALIDATION RESULTS")
    print("="*60)
    for p in passed:
        print(f"  [PASS] {p}")
    for err in errors:
        print(f"  [FAIL] {err}")
    print(f"\nTotal: {len(passed)} passed, {len(errors)} failed")
    print("="*60)
    return 0 if not errors else 1

if __name__ == "__main__":
    sys.exit(run_validation())
