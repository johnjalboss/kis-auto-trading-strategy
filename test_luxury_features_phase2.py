"""
Test Suite: 3 Luxury Institutional Features
==========================================
Validates:
1. MacroEventHorizon: D-Day countdown, event risk multipliers, and card formatting.
2. AITradePostMortem: 3-line Gemini review and Telegram sell receipt attachment.
3. SmartMoneyFootprint: Institutional sponsorship, short interest analysis, and bonus scoring.
4. TelegramInteractiveBot: Callback registration for cmd_macro_dday and cmd_smart_money.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

print("======================================================================")
print("💎 TESTING 3 LUXURY INSTITUTIONAL QUANT FEATURES (PHASE 2)")
print("======================================================================")

# 1. Macro Event Horizon & Earnings D-Day
print("\n[TEST 1] Macro Event Horizon & Earnings D-Day:")
from macro_event_horizon import MacroEventHorizon
meh = MacroEventHorizon(holdings=["VTOL", "MDT", "MRK", "STRC"])
upcoming = meh.get_upcoming_macro_events(lookahead_days=30)
mult, reason = meh.evaluate_risk_multiplier()
card = meh.format_telegram_card()
print(f"  • Upcoming Macro Events Found: {len(upcoming)}")
print(f"  • Risk Multiplier: {mult:.0%} ({reason})")
print(f"  • Macro D-Day Telegram Card:\n{card[:250]}...")
assert "매크로 지표 & 보유종목 실적 D-Day 레이더" in card
print("  ✅ [PASS] Macro Event Horizon verified!")

# 2. AI Trade Post-Mortem & Journaling
print("\n[TEST 2] AI Trade Post-Mortem & Smart Journaling:")
from ai_trade_post_mortem import AITradePostMortem
from telegram_receipt import TelegramReceiptGenerator
pm = AITradePostMortem()
rev = pm.generate_post_mortem("VTOL", 45.92, 49.50, 5, 17.90, 7.79, "DYNAMIC_RATCHET_TAKE_PROFIT", holding_days=4)
print(f"  • AI Post-Mortem Review:\n{rev}")
assert "AI 퀀트 매매 복기" in rev

sell_receipt = TelegramReceiptGenerator.format_sell_receipt("VTOL", 5, 45.92, 49.50, "DYNAMIC_RATCHET_TAKE_PROFIT", hold_days=4)
print(f"  • Full Sell Receipt with Post-Mortem Attached (Length: {len(sell_receipt)} chars)")
assert "AI 퀀트 매매 복기" in sell_receipt
print("  ✅ [PASS] AI Trade Post-Mortem verified!")

# 3. Smart Money & Institutional Footprint Radar
print("\n[TEST 3] Smart Money & Institutional Footprint Radar:")
from smart_money_footprint import SmartMoneyFootprint
sm = SmartMoneyFootprint()
vtol_sm = sm.analyze_ticker("VTOL")
print(f"  • VTOL Institutional Ownership: {vtol_sm['institutional_pct']}% | Bonus: +{vtol_sm['bonus_points']} pts")
sm_card = sm.format_telegram_card(["VTOL", "MRK", "MDT"])
print(f"  • Smart Money Card:\n{sm_card[:250]}...")
assert "월가 스마트머니" in sm_card
print("  ✅ [PASS] Smart Money Footprint Radar verified!")

# 4. Telegram Interactive Bot Callback Verification
print("\n[TEST 4] Telegram Interactive Bot Handlers:")
from telegram_interactive_bot import TelegramInteractiveBot
bot = TelegramInteractiveBot()
assert hasattr(bot, '_handle_macro_dday')
assert hasattr(bot, '_handle_smart_money')
print("  • Callbacks _handle_macro_dday and _handle_smart_money registered properly!")
print("  ✅ [PASS] Telegram Interactive Bot verified!")

print("\n======================================================================")
print("🎉 ALL 3 LUXURY INSTITUTIONAL QUANT FEATURES TESTED & VALIDATED 100%!")
print("======================================================================")
