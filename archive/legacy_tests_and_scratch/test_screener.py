import sys, os
os.chdir('/home/ubuntu/kis-auto-trading')
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')

from screener import DynamicScreener, ScreenMode
from macro import MarketRegime

def run_screener_test():
    print("=======================================")
    print("  SWING SCREENER DRY RUN TEST")
    print("=======================================")
    
    screener = DynamicScreener()
    
    # 1. RISK_ON 모드로 강제 스크리닝
    print("\n[Running RISK_ON Momentum Screen...]")
    result = screener.screen(regime=MarketRegime.RISK_ON, use_short_squeeze=False, use_momentum=True)
    
    if not result or not result.tickers:
        print("No results returned!")
        return
        
    print(f"Found {len(result.tickers)} target stocks.")
    print("\n[Top 5 Scoring Details]")
    
    # 출력 포맷팅
    for score in result.scored_stocks[:5]:
        print(f"\n{score.symbol} - Total Score: {score.total_score}")
        print(f"  Trend Quality (prev. Short Squeeze) : {score.short_squeeze_score}/25")
        print(f"  Swing Momentum Score                : {score.momentum_score}/25")
        print(f"  Inst. Accumulation (Vol Profile)    : {score.institutional_score}/20")
        print(f"  Vol Contraction (VCP/Options)       : {score.options_score}/15")
        print(f"  Technical (RSI/SMA)                 : {score.technical_score}/15")
        print(f"  Details: {score.details}")

if __name__ == "__main__":
    run_screener_test()
