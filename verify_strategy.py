import sys
import os
# Add current directory to path
sys.path.append(os.getcwd())

from strategy import _build_phase_configs, MarketPhase, get_market_phase
import config

def test_configs():
    print(f"Global ATR_STOP_MULTIPLIER: {config.ATR_STOP_MULTIPLIER}")
    print(f"Global TAKE_PROFIT_PCT: {config.TAKE_PROFIT_PCT}")
    
    configs = _build_phase_configs()
    
    midday = configs[MarketPhase.MIDDAY]
    print(f"\nMIDDAY Config:")
    print(f"  Take Profit: {midday.take_profit_pct}")
    print(f"  Stop Loss ATR: {midday.stop_loss_atr}")
    
    # Validation
    assert midday.stop_loss_atr == config.ATR_STOP_MULTIPLIER, f"Expected {config.ATR_STOP_MULTIPLIER}, got {midday.stop_loss_atr}"
    assert midday.take_profit_pct == config.TAKE_PROFIT_PCT, f"Expected {config.TAKE_PROFIT_PCT}, got {midday.take_profit_pct}"
    
    print("\n[SUCCESS] Verification SUCCESS: MIDDAY config matches global settings.")

if __name__ == "__main__":
    try:
        test_configs()
    except Exception as e:
        print(f"\n[FAILED] Verification FAILED: {e}")
        sys.exit(1)
