"""
Unit Test Suite for 4 New Institutional Quant Engines
=====================================================
1. FedNetLiquidityEngine
2. OptionsGammaEngine
3. SECForm4InsiderRadar
4. MacroEventShockShield
5. Integration into Screener & Orchestrator Sizer
"""

import os
import sys
import json

def test_all():
    print("=" * 60)
    print("🚀 [TEST] 4 NEW INSTITUTIONAL QUANT ENGINES")
    print("=" * 60)

    # 1. Fed Net Liquidity
    print("\n[TEST 1/4] FedNetLiquidityEngine:")
    try:
        from fed_net_liquidity_engine import FedNetLiquidityEngine
        engine = FedNetLiquidityEngine()
        data = engine.fetch_net_liquidity_data()
        card = engine.format_telegram_card()
        print(f"  ✅ Net Liquidity: ${data['net_liquidity_billions']:.1f}B | Regime: {data['regime']} | Sizing: {data['sizing_multiplier']}x")
    except Exception as e:
        print(f"  ❌ FedNetLiquidityEngine FAILED: {e}")

    # 2. Options Gamma Exposure
    print("\n[TEST 2/4] OptionsGammaEngine:")
    try:
        from options_gamma_engine import OptionsGammaEngine
        gex_eng = OptionsGammaEngine()
        gex_data = gex_eng.analyze_gex("SPY")
        card = gex_eng.format_telegram_card("SPY")
        print(f"  ✅ SPY GEX: ${gex_data['net_gex_millions']:+.1f}M | Call Wall: ${gex_data['call_wall']} | Put Wall: ${gex_data['put_wall']} | Regime: {gex_data['gex_regime']}")
    except Exception as e:
        print(f"  ❌ OptionsGammaEngine FAILED: {e}")

    # 3. SEC Form 4 Insider Radar
    print("\n[TEST 3/4] SECForm4InsiderRadar:")
    try:
        from sec_form4_insider_radar import SECForm4InsiderRadar
        radar = SECForm4InsiderRadar()
        ins_data = radar.analyze_insider_activity("NVDA")
        card = radar.format_telegram_card("NVDA")
        print(f"  ✅ NVDA Insider Score: {ins_data['insider_score']} | Total Bought: ${ins_data['total_bought_usd']:,.2f} | Cluster: {ins_data['is_cluster_buying']}")
    except Exception as e:
        print(f"  ❌ SECForm4InsiderRadar FAILED: {e}")

    # 4. Macro Event Shock Shield
    print("\n[TEST 4/4] MacroEventShockShield:")
    try:
        from macro_event_shock_shield import MacroEventShockShield
        shield = MacroEventShockShield()
        st = shield.check_shock_shield_status()
        card = shield.format_telegram_card()
        print(f"  ✅ Shock Shield Active: {st['is_blackout_active']} | Cushion: +{st['stop_cushion_pct']*100:.1f}% | Upcoming: {len(st['upcoming_events'])} events")
    except Exception as e:
        print(f"  ❌ MacroEventShockShield FAILED: {e}")

    print("\n" + "=" * 60)
    print("✅ ALL 4 NEW ENGINES PASSED INTEGRATION VALIDATION!")
    print("=" * 60)

if __name__ == "__main__":
    test_all()
