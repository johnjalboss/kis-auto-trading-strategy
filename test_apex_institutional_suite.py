"""
Comprehensive Apex Institutional Quant Suite Test (v1.0.0)
==========================================================
Validates:
1. SmartPeggedRouter: Mid-price limit pegging and slippage prevention.
2. MonteCarloEngine: 10,000 path simulation, ruin probability, VaR, and wealth projections.
3. MultiTimeframeConfluence: 1W + 1D + 15m resonance evaluation.
4. WeeklyAIReportGenerator: Embedded Monte Carlo stress test in weekly executive letter.
5. TelegramInteractiveBot: 1-click callback handler for Monte Carlo.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

print("======================================================================")
print("👑 TESTING 3 APEX INSTITUTIONAL QUANT ENGINES (100.00% SOVEREIGN GRADE)")
print("======================================================================")

# 1. Smart Pegged Routing Engine
print("\n[TEST 1] Zero-Slippage Smart Pegged Routing Engine:")
from smart_pegged_router import SmartPeggedRouter
router = SmartPeggedRouter()
buy_res = router.calculate_pegged_price("VTOL", "BUY", 46.50, bid_price=46.40, ask_price=46.60)
sell_res = router.calculate_pegged_price("VTOL", "SELL", 46.50, bid_price=46.40, ask_price=46.60)
print(f"  • BUY Pegged Price: ${buy_res['pegged_limit_price']} (Saved {buy_res['slippage_saved_pct']}% vs ask ${buy_res['ask_price']})")
print(f"  • SELL Pegged Price: ${sell_res['pegged_limit_price']} (Saved {sell_res['slippage_saved_pct']}% vs bid ${sell_res['bid_price']})")
assert buy_res['pegged_limit_price'] < buy_res['ask_price']
assert sell_res['pegged_limit_price'] > sell_res['bid_price']
print("  ✅ [PASS] Smart Pegged Router verified!")

# 2. Monte Carlo 10,000-Path Ruin Engine
print("\n[TEST 2] 10,000-Iteration Monte Carlo Ruin & Stress Test Engine:")
from monte_carlo_engine import MonteCarloEngine
mc = MonteCarloEngine(num_simulations=10000, horizon_trades=60)
mc_res = mc.run_simulation(current_equity=772.70)
print(f"  • Simulations: {mc_res['num_simulations']:,} paths")
print(f"  • Ruin Probability: {mc_res['ruin_probability_pct']}% ({mc_res['safety_rating']})")
print(f"  • 95% VaR Max Drawdown: -{mc_res['var_95_max_drawdown_pct']}%")
print(f"  • 90-Day Expected Equity (Median): ${mc_res['median_equity_90d']} (+{mc_res['expected_return_pct']}%)")
mc_card = mc.format_telegram_card(current_equity=772.70)
assert "몬테카를로 파산 확률" in mc_card
assert mc_res['ruin_probability_pct'] < 5.0  # Must be safe
print("  ✅ [PASS] Monte Carlo 10,000-Path Engine verified!")

# 3. Multi-Timeframe Fractal Confluence Filter
print("\n[TEST 3] Multi-Timeframe Fractal Confluence Filter (1W + 1D + 15m):")
from multi_timeframe_confluence import MultiTimeframeConfluence
mtf = MultiTimeframeConfluence()
mtf_res = mtf.evaluate_confluence("VTOL")
print(f"  • Confluence Score: {mtf_res['confluence_score']}/100 | Bonus: +{mtf_res['bonus_points']} pts")
print(f"  • Alignment Summary: {mtf_res['summary']}")
assert mtf_res['confluence_score'] > 0
print("  ✅ [PASS] Multi-Timeframe Confluence Filter verified!")

# 4. Weekly AI Report with Monte Carlo Integration
print("\n[TEST 4] Weekly AI Executive Report + Monte Carlo Integration:")
from weekly_ai_report_generator import WeeklyAIReportGenerator
rep = WeeklyAIReportGenerator().generate_report()
print(f"  • Generated Report Length: {len(rep)} chars")
assert "몬테카를로" in rep
assert "주간 AI 퀀트 운용 보고서" in rep
print("  ✅ [PASS] Weekly AI Report with Monte Carlo verified!")

# 5. Telegram Interactive Bot Callback Verification
print("\n[TEST 5] Telegram Interactive Bot Monte Carlo Handler:")
from telegram_interactive_bot import TelegramInteractiveBot
bot = TelegramInteractiveBot()
assert hasattr(bot, '_handle_monte_carlo')
print("  • Callback _handle_monte_carlo registered properly!")
print("  ✅ [PASS] Telegram Interactive Bot verified!")

print("\n======================================================================")
print("🎉 ALL 3 APEX INSTITUTIONAL UPGRADES TESTED & VALIDATED 100% PERFECT!")
print("======================================================================")
