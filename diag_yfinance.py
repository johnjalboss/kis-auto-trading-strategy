import yfinance as yf
import pandas as pd
import numpy as np

symbols = ['SPY', 'QQQ', 'GLD', 'TLT']
data = yf.download(symbols, period='3mo', progress=False)
print("Raw columns:", data.columns)
print("Raw data head:\n", data.head(2))

# Close 추출 방식 검증
if 'Close' in data.columns:
    close_data = data['Close']
    print("Close data type:", type(close_data))
    print("Close data columns:", close_data.columns if isinstance(close_data, pd.DataFrame) else "No columns (Series)")
    
    returns = close_data.pct_change().dropna()
    corr_matrix = returns.corr()
    print("Corr matrix columns:", corr_matrix.columns)
    print("Corr matrix index:", corr_matrix.index)
    
    # 각 셀 추출 검증
    try:
        spy_qqq = corr_matrix.loc['SPY', 'QQQ']
        print(f"spy_qqq: {spy_qqq} (type: {type(spy_qqq)})")
    except Exception as e:
        print("Error accessing corr_matrix.loc['SPY', 'QQQ']:", e)
else:
    print("'Close' column not found in raw data")
