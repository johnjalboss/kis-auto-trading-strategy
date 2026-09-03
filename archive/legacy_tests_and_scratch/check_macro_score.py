import sys
from loguru import logger
logger.remove()  # Suppress internal logs to keep output clean

# Add current dir to import paths if needed
import os
sys.path.append(os.getcwd())

try:
    from global_macro import get_macro_module
    from fed_watch import get_fed_analyzer
    from geopolitical import get_geopolitical
    from intermarket import get_intermarket_analyzer
    from options_metrics import get_options_analyzer
    from news_analyzer import get_news_analyzer
    from economic_calendar import get_calendar
    from social_sentiment import get_social_sentiment
    
    # Init modules
    global_macro = get_macro_module()
    fed = get_fed_analyzer()
    geo = get_geopolitical()
    intermarket = get_intermarket_analyzer()
    options = get_options_analyzer()
    
    # We will score just these top macro metrics to simulate the phase 2 output
    
    # 1. Global Macro (Weight: 2.0)
    g_res = global_macro.analyze()
    g_score = g_res.macro_score
    print(f"Global Macro: {g_score} (Weight: 2.0) -> {g_res.signal}")
    print(f"   Triggers: {g_res.triggers}")
    
    # 2. Fed Watch (Weight: 1.5)
    f_res = fed.analyze()
    f_score = f_res.fed_score
    print(f"\nFed Watch: {f_score} (Weight: 1.5) -> {f_res.signal}")
    print(f"   Details: {f_res.details}")
    
    # 3. Geopolitical (Weight: 1.5)
    geo_res = geo.analyze()
    geo_score = 100 - geo_res.risk_score  # lower risk = better score
    if geo_res.overall_risk_level == "HIGH":
        geo_score = -50
    elif geo_res.overall_risk_level == "EXTREME":
        geo_score = -100
    print(f"\nGeopolitical: {geo_score} (Risk: {geo_res.risk_score}, Weight: 1.5) -> {geo_res.overall_risk_level}")
    print(f"   Rec: {geo_res.recommendation}")
    
    # 4. Intermarket (Weight: 1.0)
    int_res = intermarket.analyze()
    int_score = int_res.composite_score
    print(f"\nIntermarket: {int_score} (Weight: 1.0) -> Risk: {int_res.risk_appetite}")
    
    # Calculate weighted total
    total_weight = 2.0 + 1.5 + 1.5 + 1.0
    weighted_score = (g_score * 2.0 + f_score * 1.5 + geo_score * 1.5 + int_score * 1.0) / total_weight
    
    print(f"\n{'='*40}")
    print(f"TOTAL ESTIMATED MACRO SCORE: {weighted_score:.2f}")
    print(f"{'='*40}")
    
    if weighted_score < -20:
        print("STATUS: RISK-OFF (Very unstable)")
    elif weighted_score < 0:
        print("STATUS: CAUTIOUS (Slightly unstable)")
    else:
        print("STATUS: RISK-ON (Favorable)")

except Exception as e:
    print("Error analyzing macro:", e)
    import traceback
    traceback.print_exc()
