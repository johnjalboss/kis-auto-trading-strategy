import sys, os
os.chdir('/home/ubuntu/kis-auto-trading')
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')

from sector_rotator import get_sector_rotator
sr = get_sector_rotator()
for sym in ['AAPL', 'XOM', 'JPM', 'TSLA', 'MRNA', 'GE', 'WMT', 'NVDA', 'META']:
    etf = sr.get_sector_for_stock(sym)
    print(f"{sym}: {etf}")
