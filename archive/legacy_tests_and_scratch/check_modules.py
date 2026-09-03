import sys
sys.path.insert(0, '.')

modules_to_check = [
    'earnings_analyzer', 'earnings_calendar', 'insider_tracker',
    'news_analyzer', 'social_sentiment', 'sentiment',
    'options_flow', 'options_metrics', 'order_flow',
    'smart_money', 'market_breadth', 'market_internals',
    'etf_flows', 'sector_fund_flow', 'short_squeeze',
    'crypto_sentiment', 'geopolitical', 'intermarket',
    'fundamental_analyzer', 'factor_analysis', 'seasonality',
    'fed_watch', 'vix_structure', 'global_macro', 'macro',
]

ok_modules = []
fail_modules = []

for m in modules_to_check:
    try:
        mod = __import__(m)
        ok_modules.append(m)
    except Exception as e:
        fail_modules.append((m, str(e)[:80]))

print("=== 동작하는 데이터 모듈 ===")
for m in ok_modules:
    print("  OK:", m)

print("")
print("=== 오류 모듈 ===")
for m, e in fail_modules:
    print("  FAIL:", m, "|", e)
