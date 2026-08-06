import re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mods = [
    'credit_spreads','crypto_sentiment','etf_flows','fed_watch','geopolitical',
    'global_macro','hidden_markov_regime','intermarket','macro','market_breadth',
    'market_internals','market_psychology','oil_impact','sector_rotation',
    'sector_rotator','vix_structure','yen_carry'
]

for m in mods:
    try:
        src = open(f'{m}.py','r',encoding='utf-8',errors='replace').read()
        sig = re.search(r'def analyze\([^)]*\)', src)
        sig_str = sig.group(0) if sig else 'NOT FOUND'
        # Also check if it inherits BaseAnalyzer
        base = 'BaseAnalyzer' in src
        print(f'{m}: sig={sig_str[:70]}, has_base={base}')
    except Exception as e:
        print(f'{m}: ERROR {e}')
