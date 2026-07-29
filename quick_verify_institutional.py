import pandas as pd
import numpy as np
from loguru import logger
import data_proxy # Important to patch yfinance
from fx_risk import FXRiskAnalyzer
from earnings_quality import EarningsQualityScorer
from estimate_revision import EstimateRevisionAnalyzer
from short_squeeze import ShortSqueezeMonitor
from economic_surprise import EconomicSurpriseAnalyzer
from signal_aggregator import get_signal_aggregator

def test_institutional():
    print("=== Institutional Module Verification ===")
    df_dummy = pd.DataFrame({"Close": [1300 + i for i in range(100)]})
    df_dummy["Volume"] = 1000000
    
    analyzers = [
        FXRiskAnalyzer(),
        EarningsQualityScorer(),
        EstimateRevisionAnalyzer(),
        ShortSqueezeMonitor(),
        EconomicSurpriseAnalyzer()
    ]
    
    symbols = ["AAPL", "TSLA", "NVDA"]
    
    for symbol in symbols:
        print(f"\nTesting {symbol}:")
        for a in analyzers:
            try:
                res = a.analyze(df_dummy, symbol=symbol)
                print(f" - {a.name}: score={res['score']}, signals={res['signals']}")
            except Exception as e:
                print(f" - {a.__class__.__name__} FAILED: {e}")

    print("\nTesting Aggregator Integration (AAPL):")
    agg = get_signal_aggregator()
    res_agg = agg.analyze(df_dummy, symbol="AAPL")
    print(f" - Aggregator Institutional Score: {res_agg.institutional_score}")
    print(f" - Aggregator Details: {res_agg.details}")
    print(f" - Total Bonus Score: {res_agg.bonus_score}")

if __name__ == "__main__":
    test_institutional()
