import hashlib, os

files = [
    'auto_tuning_engine.py',
    'post_exit_tracker.py',
    'strategy.py',
    'orchestrator.py',
    'screener.py',
    'data_proxy.py',
    'telegram_receipt.py',
    'premarket_gap_sniper.py',
    'telegram_interactive_bot.py'
]

for f in files:
    fpath = os.path.join('/home/ubuntu/kis-auto-trading', f)
    if os.path.exists(fpath):
        with open(fpath, 'rb') as fp:
            h = hashlib.sha256(fp.read()).hexdigest()
        print(f'{f}: {h[:16]}... OK')
    else:
        print(f'{f}: MISSING')