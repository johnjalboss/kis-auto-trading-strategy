import pandas as pd
import yfinance as yf
from loguru import logger
import sys

# Import new modules
from short_squeeze import ShortSqueezeMonitor
from earnings_quality import EarningsQualityScorer
from estimate_revision import EstimateRevisionAnalyzer
from fx_risk import FXRiskAnalyzer
from economic_surprise import EconomicSurpriseAnalyzer

def hard_audit():
    symbol = "HST"
    print(f"\n{'#'*60}")
    print(f"### HARD TRUTH AUDIT: PROVING MODULE EXECUTION ({symbol}) ###")
    print(f"{'#'*60}\n")
    
    # Setup data
    df = yf.download(symbol, period="1mo", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    modules = [
        ShortSqueezeMonitor(),
        EarningsQualityScorer(),
        EstimateRevisionAnalyzer(),
        FXRiskAnalyzer(),
        EconomicSurpriseAnalyzer()
    ]
    
    results = []
    
    for mod in modules:
        print(f"--- Testing Module: {mod.name} ({mod.category}) ---")
        try:
            # Check is_symbol_dependent
            is_dep = getattr(mod, 'is_symbol_dependent', 'MISSING')
            print(f"  [Interface Verify] is_symbol_dependent: {is_dep}")
            
            # Execute
            result = mod.analyze(df, symbol=symbol)
            
            # Print Proof
            print(f"  [Execution Result] Score: {result.get('score', 0)}")
            print(f"  [Execution Result] Signals: {result.get('signals', [])}")
            
            if result.get('score') != 0 or len(result.get('signals', [])) > 0:
                print(f"  ✅ VERIFIED: Module is producing data.")
                results.append(True)
            else:
                print(f"  ⚠️ WARNING: Module returned zero/empty. Check data source.")
                results.append(False)
        except Exception as e:
            print(f"  ❌ FAILED: Module crashed with error: {e}")
            results.append(False)
        print("-" * 40)

    success_count = sum(results)
    print(f"\n{'='*60}")
    print(f"AUDIT SUMMARY: {success_count}/{len(modules)} Modules Operational")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    logger.remove() # Silence logging for clean output
    hard_audit()
