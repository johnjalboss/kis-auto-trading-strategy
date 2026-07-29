import sys
import os
import pandas as pd
# Add current directory to path
sys.path.insert(0, os.getcwd())

import base_adapters
import reporter
import momentum_ranking
import sentiment

def test(name, fn):
    try:
        fn()
        print(f'PASS: {name}')
    except Exception as e:
        print(f'FAIL: {name} - {type(e).__name__}: {e}')
        import traceback
        traceback.print_exc()

# 1. base_adapters blacklist
def t1():
    adapters = base_adapters.get_available_adapters()
    names = [a.__name__ for a in adapters]
    # Check if CandlePattern or CandlePatternAdapter exists
    bad = [n for n in names if 'CandlePattern' in n]
    assert not bad, f'CandlePattern still discovered: {bad}'
test('base_adapters blacklist', t1)

# 2. reporter alias
def t2():
    from reporter import TradingReporter
    assert TradingReporter is not None, 'TradingReporter not found'
test('reporter alias', t2)

# 3. momentum_ranking analyze (Pandas ambiguity fix)
def t3():
    ranker = momentum_ranking.MomentumRanker()
    # Mocking yf.download to avoid network calls
    import kis_data
    old_download = kis_data.download
    kis_data.download = lambda *args, **kwargs: pd.DataFrame({'Close': [100.0]*252})
    try:
        res = ranker.analyze('AAPL')
        assert res.ranking_score is not None
    finally:
        kis_data.download = old_download
test('momentum_ranking.analyze()', t3)

# 4. sentiment analyze (Pandas ambiguity fix)
def t4():
    analyzer = sentiment.SentimentAnalyzer()
    res = analyzer.analyze('AAPL')
    assert res.score is not None
test('sentiment.analyze()', t4)

# 5. base_adapters UniversalAdapter symbol handling
def t5():
    from base_adapters import get_available_adapters
    import pandas as pd
    df = pd.DataFrame({'Close': [100.0]*252})
    adapters = get_available_adapters()
    targets = [a for a in adapters if a.__name__ in ['MomentumRankerAdapter', 'SentimentAnalyzerAdapter']]
    for A in targets:
        inst = A()
        # This will pass df as first arg in UniversalAdapter.analyze
        res = inst.analyze(df, symbol='AAPL')
        assert 'score' in res, f'Analyze failed for {A.__name__}'
test('UniversalAdapter symbol handling', t5)
