from screener import DynamicScreener, ScreenMode
import kis_data

screener = DynamicScreener()

symbols = ["MRK", "MDT", "VTOL", "STRC", "NVDA", "AAPL", "PLTR", "LLY", "ABBV", "TSLA"]

print("=== STOCK SCORING BREAKDOWN ===")
for sym in symbols:
    score_obj = screener._score_stock(sym, mode=ScreenMode.MOMENTUM)
    if score_obj:
        print(f"\n[{sym:5s}] Total Score: {score_obj.total_score:2d}/100 | Near 52W: {score_obj.near_52w_high}")
        print(f"  ShortSqueeze: {score_obj.short_squeeze_score:2d} | Momentum: {score_obj.momentum_score:2d} | Inst: {score_obj.institutional_score:2d} | Tech: {score_obj.technical_score:2d} | Opt: {score_obj.options_score:2d}")
        print(f"  Details: {score_obj.details}")
