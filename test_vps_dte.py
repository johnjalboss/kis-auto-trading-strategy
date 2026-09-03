import sys
sys.path.append('/home/ubuntu/kis-auto-trading')
from dealer_gex_radar import DealerGEXRadar
r = DealerGEXRadar()
for sym in ['SPY', 'NVDA', 'BEN', 'AAPL']:
    res = r.analyze(sym)
    exp = res.get('nearest_expiration')
    dte = res.get('dte_days')
    print(f'{sym:5s} -> Expiry: {exp} | DTE: {dte}d')