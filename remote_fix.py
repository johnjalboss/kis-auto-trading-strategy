
import os
path = '/home/ubuntu/kis-auto-trading/remote_orchestrator.py'
with open(path, 'r') as f:
    content = f.read()

old = '''        # 4. Kelly Criterion + Position Sizing
        try:
            from position_sizer import calculate_optimal_size
            from kelly_criterion import get_kelly_fraction
            kelly_pct = get_kelly_fraction(symbol)
            qty = calculate_optimal_size(symbol, qty, kelly_pct, self.state.max_exposure_pct)
        except Exception as err:
            logger.warning("⚠️ [remote_fix.py] Fallback triggered: {}", err)
            
        if qty <= 0:
            logger.warning("Risk modules reduced size to 0 for {}", symbol)
            return'''

new = '''        # 4. Kelly Criterion + Position Sizing (ONLY for BUY orders)
        if action == "BUY":
            try:
                from position_sizer import calculate_optimal_size
                from kelly_criterion import get_kelly_fraction
                kelly_pct = get_kelly_fraction(symbol)
                qty = calculate_optimal_size(symbol, qty, kelly_pct, self.state.max_exposure_pct)
            except Exception as err:
                logger.warning("⚠️ [remote_fix.py] Fallback triggered: {}", err)
            
            if qty <= 0:
                logger.warning("Risk modules reduced size to 0 for {}", symbol)
                return
        else:
            # For SELL/CLOSE, ensure we use the full requested quantity
            pass'''

if old in content:
    with open(path, 'w') as f:
        f.write(content.replace(old, new))
    print("SUCCESS")
else:
    print("NOT FOUND")
