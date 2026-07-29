import os
import sys
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from typing import Dict, List

print("=" * 75)
print("LONG-TERM CORE QUANT ENGINE: 2020 - PRESENT BACKTEST VS QQQ")
print("=" * 75)

# 1. Configuration
tickers = ["AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "WPC", "XOM", "JPM", "SO", "LLY"]
benchmark_ticker = "QQQ"
initial_capital = 100000000.0  # 1억 원

# 2. Fetch Historical Price Data (2020 - Present)
start_str = "2020-01-01"
end_str = datetime.now().strftime('%Y-%m-%d')

print(f"\n[1/3] Downloading 6-year price data for {len(tickers)} stocks and QQQ...")
prices_df = yf.download(tickers, start=start_str, end=end_str, progress=False)['Close']
highs_df = yf.download(tickers, start=start_str, end=end_str, progress=False)['High']
lows_df = yf.download(tickers, start=start_str, end=end_str, progress=False)['Low']
volumes_df = yf.download(tickers, start=start_str, end=end_str, progress=False)['Volume']
benchmark_df = yf.download(benchmark_ticker, start=start_str, end=end_str, progress=False)['Close']

if hasattr(prices_df.columns, 'get_level_values'):
    prices_df.columns = prices_df.columns.get_level_values(0)
    highs_df.columns = highs_df.columns.get_level_values(0)
    lows_df.columns = lows_df.columns.get_level_values(0)
    volumes_df.columns = volumes_df.columns.get_level_values(0)

# Force benchmark to be a 1D Series
if isinstance(benchmark_df, pd.DataFrame):
    benchmark_df = benchmark_df.iloc[:, 0]

# Fill missing values
prices_df = prices_df.ffill().bfill()
highs_df = highs_df.ffill().bfill()
lows_df = lows_df.ffill().bfill()
volumes_df = volumes_df.ffill().bfill()
benchmark_df = benchmark_df.ffill().bfill()

# 3. Gather Current Fundamentals (used as baseline)
print("[2/3] Accessing baseline parameters for backtest...")
fundamentals = {}
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
    except:
        fundamentals[sym] = {'eps': 1.0, 'peg': 1.0, 'sector': '', 'earningsGrowth': 0.1}

# 4. Simulation Setup
print("\n[3/3] Running simulation from 2020 to present...")

# Technical indicators preparation
sma20 = prices_df.rolling(20).mean()
sma50 = prices_df.rolling(50).mean()
sma200 = prices_df.rolling(200).mean()

# RSI helper
def get_rsi_df(df, period=14):
    delta = df.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1)
    return 100 - (100 / (1 + rs))

rsi_df = get_rsi_df(prices_df)

# Volume SMA preparation
volume_sma20 = volumes_df.rolling(20).mean()

# Simulation state
capital = initial_capital
cash = capital
shares = {sym: 0.0 for sym in tickers}
portfolio_values = []
dates = prices_df.index[200:]  # Warmup for 200 SMA

max_positions = 5
target_weight = 1.0 / max_positions

for i in range(len(dates)):
    current_date = dates[i]
    
    # Calculate daily candidates using 6-Category Scoring Logic
    daily_candidates = []
    
    # Calculate Market Regime from QQQ (Macro component)
    qqq_price = benchmark_df.loc[current_date]
    qqq_sma200 = benchmark_df.rolling(200).mean().loc[current_date]
    regime_score = 50
    if not np.isnan(qqq_sma200):
        if qqq_price > qqq_sma200:
            regime_score = 75  # Bull market macro score
        else:
            regime_score = 25  # Bear market macro score
            
    for sym in tickers:
        price = prices_df.loc[current_date, sym]
        
        # 1. Technical Score (25%)
        tech_score = 50
        if price > sma20.loc[current_date, sym] > sma50.loc[current_date, sym]:
            tech_score = 85
        elif price < sma20.loc[current_date, sym]:
            tech_score = 30
            
        # 2. Fundamental Score (20%) - Implements our NEW PE & PEG Logic
        eps = fundamentals[sym]['eps']
        peg_base = fundamentals[sym]['peg']
        sector = fundamentals[sym]['sector']
        sector_lower = sector.lower()
        daily_pe = price / eps if eps > 0 else 0
        daily_peg = daily_pe / (fundamentals[sym]['earningsGrowth'] * 100) if fundamentals[sym]['earningsGrowth'] > 0 else peg_base
        
        pe_value_score = 50
        if daily_pe > 0:
            if any(x in sector_lower for x in ['technology', 'healthcare', 'communication']):
                pe_value_score = 90 if daily_pe < 25 else (70 if daily_pe < 45 else (50 if daily_pe < 65 else 30))
            elif any(x in sector_lower for x in ['utility', 'financial', 'real estate', 'energy']):
                pe_value_score = 90 if daily_pe < 12 else (70 if daily_pe < 20 else (50 if daily_pe < 30 else 30))
            else:
                pe_value_score = 90 if daily_pe < 15 else (70 if daily_pe < 25 else (50 if daily_pe < 40 else 30))
                
        if daily_peg > 0:
            peg_score = 95 if daily_peg < 1.0 else (75 if daily_peg < 1.5 else (50 if daily_peg < 2.5 else 25))
            fund_score = int(pe_value_score * 0.6 + peg_score * 0.4)
        else:
            fund_score = pe_value_score
            
        # 3. Smart Money & Sentiment Score (20%) - Volume Surge + Breakout
        sentiment_score = 50
        # Volume Surge check
        vol = volumes_df.loc[current_date, sym]
        v_sma = volume_sma20.loc[current_date, sym]
        if v_sma > 0 and vol / v_sma > 1.5:
            sentiment_score += 15
        # 20-day high breakout check
        past_idx = prices_df.index.get_loc(current_date)
        if past_idx >= 20:
            high_20d = prices_df.iloc[past_idx-20:past_idx][sym].max()
            if price > high_20d:
                sentiment_score += 20
                
        # 4. Risk Score (15%) - Volatility drag penalty
        risk_score = 50
        # Volatility check (High/Low spread)
        high = highs_df.loc[current_date, sym]
        low = lows_df.loc[current_date, sym]
        spread_pct = (high - low) / price * 100 if price > 0 else 0
        if spread_pct > 3.0:
            risk_score = 30  # High volatility penalty
        elif spread_pct < 1.2:
            risk_score = 70  # Low volatility advantage
            
        # Composite Weighted Score
        composite_score = int(
            tech_score * 0.25 +
            fund_score * 0.20 +
            regime_score * 0.20 +
            sentiment_score * 0.20 +
            risk_score * 0.15
        )
        
        daily_candidates.append((sym, composite_score, price))
        
    # Sort candidates
    daily_candidates.sort(key=lambda x: x[1], reverse=True)
    selected = daily_candidates[:max_positions]
    selected_symbols = [x[0] for x in selected]
    
    # Portfolio Evaluation
    portfolio_value = cash + sum(shares[sym] * prices_df.loc[current_date, sym] for sym in tickers)
    portfolio_values.append(portfolio_value)
    
    # Weekly Rebalancing
    if i % 5 == 0:
        # Liquidate assets not in selected list
        for sym in tickers:
            if sym not in selected_symbols and shares[sym] > 0:
                cash += shares[sym] * prices_df.loc[current_date, sym]
                shares[sym] = 0.0
                
        # Reallocate equally
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

# Final Performance stats
final_portfolio_value = portfolio_values[-1]
strategy_return = (final_portfolio_value - initial_capital) / initial_capital * 100

# Benchmark return
start_idx = prices_df.index.get_loc(dates[0])
qqq_start = benchmark_df.iloc[start_idx]
qqq_end = benchmark_df.iloc[-1]
qqq_return = (qqq_end - qqq_start) / qqq_start * 100

# MDDs
portfolio_series = pd.Series(portfolio_values)
roll_max = portfolio_series.cummax()
drawdown = (portfolio_series - roll_max) / roll_max * 100
strategy_max_dd = drawdown.min()

qqq_values = benchmark_df.values.flatten()
qqq_series = pd.Series(qqq_values[start_idx:])
qqq_roll_max = qqq_series.cummax()
qqq_drawdown = (qqq_series - qqq_roll_max) / qqq_roll_max * 100
benchmark_max_dd = qqq_drawdown.min()

alpha = strategy_return - qqq_return

print("\n" + "=" * 75)
print("FINAL LONG-TERM BACKTEST RESULT: 2020 - PRESENT")
print("=" * 75)
print(f"Period:           {dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}")
print(f"Initial Capital:  {initial_capital:,.0f} KRW")
print(f"Final Capital:    {final_portfolio_value:,.0f} KRW")
print("-" * 75)
print(f"Strategy Return:  {strategy_return:+.2f}%")
print(f"Benchmark (QQQ):  {qqq_return:+.2f}%")
print(f"Alpha (Outperf):  {alpha:+.2f}%")
print("-" * 75)
print(f"Strategy Max DD:  {strategy_max_dd:.2f}%")
print(f"Benchmark Max DD: {benchmark_max_dd:.2f}%")
print("=" * 75)
if alpha > 0:
    print(f"SUCCESS: The complete strategy beat QQQ by {alpha:.2f}%!")
else:
    print(f"Strategy: {strategy_return:.2f}% | QQQ: {qqq_return:.2f}%")
print("=" * 75)
