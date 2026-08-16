from screener import DynamicScreener, MarketRegime
from composite_signal import CompositeSignalEngine
from kis_data import download

screener = DynamicScreener()

print("=== SCORING MRK ===")
mrk_score = screener._score_stock("MRK", regime=MarketRegime.RISK_ON)
print("MRK Score Object:", mrk_score)
if mrk_score:
    print(f"Total Score: {mrk_score.total_score}")
    print(f"Details: {mrk_score.details}")

print("\n=== TOP 10 RANKED STOCKS FROM SCREENER ===")
res = screener.screen(regime=MarketRegime.RISK_ON)
print("Screen mode:", res.mode)
print(f"Total screened tickers: {len(res.tickers)}")
for i, s in enumerate(res.scores[:10], 1):
    print(f"#{i:02d} {s.symbol:6s} | Total: {s.total_score:2d} | Mom: {s.momentum_score:2d} | Tech: {s.technical_score:2d} | Inst: {s.institutional_score:2d}")
