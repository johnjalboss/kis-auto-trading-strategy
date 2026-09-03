import yfinance as yf
ben = yf.Ticker('BEN')
hist = ben.history(period='1d', interval='1m')
if not hist.empty:
    curr = hist['Close'].iloc[-1]
    entry = 35.41
    pnl = (curr - entry) / entry * 100
    print(f'BEN Current Price:  | Entry:  | PnL: {pnl:+.2f}%')