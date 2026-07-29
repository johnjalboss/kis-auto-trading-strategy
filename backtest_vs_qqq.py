import os
import sys
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List

# Load local fundamental_analyzer
sys.path.append(r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading")
from fundamental_analyzer import FundamentalAnalyzer

print("=" * 70)
print("QUANT BACKTEST ENGINE: STRATEGY VS QQQ (NASDAQ-100)")
print("=" * 70)

# 1. Targets and Benchmark
tickers = ["AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "WPC", "XOM", "JPM", "SO", "LLY"]
benchmark_ticker = "QQQ"
initial_capital = 100000000.0  # 100,000,000 KRW (1억 원)

# 2. Fetch Historical Price Data (1 Year)
end_date = datetime.now()
start_date = end_date - timedelta(days=365)
start_str = start_date.strftime('%Y-%m-%d')
end_str = end_date.strftime('%Y-%m-%d')

print(f"\n[1/3] Downloading price data for {len(tickers)} stocks and benchmark...")
prices_df = yf.download(tickers, start=start_str, end=end_str, progress=False)['Close']
benchmark_df = yf.download(benchmark_ticker, start=start_str, end=end_str, progress=False)['Close']

if hasattr(prices_df.columns, 'get_level_values'):
    prices_df.columns = prices_df.columns.get_level_values(0)

# Force benchmark to be a 1D Series to prevent dimension errors
if isinstance(benchmark_df, pd.DataFrame):
    benchmark_df = benchmark_df.iloc[:, 0]
elif hasattr(benchmark_df, 'columns'):
    benchmark_df = pd.Series(benchmark_df.values.flatten(), index=benchmark_df.index)

# Fill missing values
prices_df = prices_df.ffill().bfill()
benchmark_df = benchmark_df.ffill().bfill()

# 3. Gather Current Fundamentals to reconstruct historical fundamentals
print("[2/3] Gathering fundamental parameters from yfinance...")
fundamentals = {}
fa = FundamentalAnalyzer()

for sym in tickers:
    try:
        ticker = yf.Ticker(sym)
        info = ticker.info
        fundamentals[sym] = {
            'eps': info.get('trailingEps', 0) or 1.0,
            'peg': info.get('pegRatio', 0) or 1.0,
            'sector': info.get('sector', '') or '',
            'earningsGrowth': info.get('earningsGrowth', 0) or 0.1
        }
    except Exception as e:
        fundamentals[sym] = {'eps': 1.0, 'peg': 1.0, 'sector': '', 'earningsGrowth': 0.1}

# 4. Simulation Loop
print("\n[3/3] Simulating Portfolio Allocation based on New Valuation Scoring...")

# Simulation state
capital = initial_capital
cash = capital
shares = {sym: 0.0 for sym in tickers}
portfolio_values = []
dates = prices_df.index

# Backtest parameters
max_positions = 5
target_weight = 1.0 / max_positions  # Equal weight for top selected

for i in range(len(dates)):
    current_date = dates[i]
    
    # Calculate daily scores for all tickers based on daily PE and PEG
    daily_candidates = []
    
    for sym in tickers:
        price = prices_df.loc[current_date, sym]
        eps = fundamentals[sym]['eps']
        peg_base = fundamentals[sym]['peg']
        sector = fundamentals[sym]['sector']
        sector_lower = sector.lower()
        
        # Calculate daily PE: PE = Price / EPS
        daily_pe = price / eps if eps > 0 else 0
        
        # Calculate daily PEG
        daily_peg = daily_pe / (fundamentals[sym]['earningsGrowth'] * 100) if fundamentals[sym]['earningsGrowth'] > 0 else peg_base
        
        # Evaluate using our new scoring logic
        pe_value_score = 50
        details = []
        if daily_pe > 0:
            if any(x in sector_lower for x in ['technology', 'healthcare', 'communication']):
                if daily_pe < 25: pe_value_score = 90
                elif daily_pe < 45: pe_value_score = 70
                elif daily_pe < 65: pe_value_score = 50
                else: pe_value_score = 30
            elif any(x in sector_lower for x in ['utility', 'financial', 'real estate', 'energy']):
                if daily_pe < 12: pe_value_score = 90
                elif daily_pe < 20: pe_value_score = 70
                elif daily_pe < 30: pe_value_score = 50
                else: pe_value_score = 30
            else:
                if daily_pe < 15: pe_value_score = 90
                elif daily_pe < 25: pe_value_score = 70
                elif daily_pe < 40: pe_value_score = 50
                else: pe_value_score = 30
                
        if daily_peg > 0:
            if daily_peg < 1.0: peg_score = 95
            elif daily_peg < 1.5: peg_score = 75
            elif daily_peg < 2.5: peg_score = 50
            else: peg_score = 25
            value_score = int(pe_value_score * 0.6 + peg_score * 0.4)
        else:
            value_score = pe_value_score
            
        daily_candidates.append((sym, value_score, price))
    
    # Sort candidates by Value Score descending
    daily_candidates.sort(key=lambda x: x[1], reverse=True)
    selected = daily_candidates[:max_positions]
    selected_symbols = [x[0] for x in selected]
    
    # Current portfolio valuation
    portfolio_value = cash + sum(shares[sym] * prices_df.loc[current_date, sym] for sym in tickers)
    portfolio_values.append(portfolio_value)
    
    # Simple Weekly Rebalancing
    if i % 5 == 0:  # Every 5 trading days
        # Liquidate assets not in selected
        for sym in tickers:
            if sym not in selected_symbols and shares[sym] > 0:
                cash += shares[sym] * prices_df.loc[current_date, sym]
                shares[sym] = 0.0
                
        # Allocate to selected
        target_allocation_val = portfolio_value * target_weight
        for sym, score, price in selected:
            current_holding_val = shares[sym] * price
            diff = target_allocation_val - current_holding_val
            
            if diff > 0 and cash >= diff:
                shares[sym] += diff / price
                cash -= diff
            elif diff < 0:
                shares_to_sell = abs(diff) / price
                shares[sym] -= shares_to_sell
                cash += abs(diff)

# Calculate results
final_portfolio_value = portfolio_values[-1]
total_return = (final_portfolio_value - initial_capital) / initial_capital * 100

# Benchmark return (QQQ)
qqq_start = benchmark_df.iloc[0]
qqq_end = benchmark_df.iloc[-1]
qqq_return = (qqq_end - qqq_start) / qqq_start * 100

# Calculate MDD
portfolio_series = pd.Series(portfolio_values)
roll_max = portfolio_series.cummax()
drawdown = (portfolio_series - roll_max) / roll_max * 100
max_dd = drawdown.min()

# Benchmark MDD
qqq_series = pd.Series(benchmark_df.values)
qqq_roll_max = qqq_series.cummax()
qqq_drawdown = (qqq_series - qqq_roll_max) / qqq_roll_max * 100
qqq_max_dd = qqq_drawdown.min()

alpha = total_return - qqq_return

print("\n" + "=" * 70)
print("BACKTEST RESULT: STRATEGY VS QQQ")
print("=" * 70)
print(f"Period:           {start_str} to {end_str}")
print(f"Initial Capital:  {initial_capital:,.0f} KRW")
print(f"Final Capital:    {final_portfolio_value:,.0f} KRW")
print("-" * 70)
print(f"Strategy Return:  {total_return:+.2f}%")
print(f"Benchmark (QQQ):  {qqq_return:+.2f}%")
print(f"Alpha (Outperf):  {alpha:+.2f}%")
print("-" * 70)
print(f"Strategy Max DD:  {max_dd:.2f}%")
print(f"Benchmark Max DD: {qqq_max_dd:.2f}%")
print("=" * 70)
if alpha > 0:
    print(f"SUCCESS: The new Valuation Strategy beat QQQ by {alpha:.2f}%!")
else:
    print(f"INFO: Underperformed QQQ by {abs(alpha):.2f}% in this period.")
print("=" * 70)
