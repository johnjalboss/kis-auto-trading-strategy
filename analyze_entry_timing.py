"""
Analyze past trades to find data-driven thresholds for overextension penalty.
Questions:
1. When we bought, what was the stock's % gain from SMA20?
2. What was the 5-day return before entry?
3. What was the RSI at entry?
4. Did those trades end in profit or loss?
"""
import json
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def main():
    try:
        with open('portfolio_trades.json', 'r', encoding='utf-8') as f:
            trades = json.load(f)
    except FileNotFoundError:
        print("portfolio_trades.json not found.")
        return

    # Focus on BUY trades that have a matching SELL
    buys = {t['symbol']: t for t in trades if t['type'] == 'BUY'}
    sells = [t for t in trades if t['type'] == 'SELL']

    results = []
    print(f"Analyzing {len(buys)} buy trades... (fetching price data)\n")

    for sell in sells:
        sym = sell['symbol']
        if sym not in buys:
            continue
        buy = buys[sym]
        
        buy_date = pd.Timestamp(buy['date'])
        buy_price = buy['price']
        sell_price = sell['price']
        pnl_pct = (sell_price - buy_price) / buy_price * 100
        
        # Fetch daily data ending at buy date
        try:
            start = (buy_date - timedelta(days=90)).strftime('%Y-%m-%d')
            end = (buy_date + timedelta(days=2)).strftime('%Y-%m-%d')
            df = yf.download(sym, start=start, end=end, progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if df is None or len(df) < 25:
                continue
            
            close = df['Close']
            sma20 = close.rolling(20).mean().iloc[-1]
            sma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else sma20
            current = float(close.iloc[-1])
            
            # RSI
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss.replace(0, 1)
            rsi = float((100 - (100 / (1 + rs))).iloc[-1])
            
            # % distance above SMA20
            dist_sma20 = (current - float(sma20)) / float(sma20) * 100
            
            # 5-day return before entry
            ret_5d = (float(close.iloc[-1]) / float(close.iloc[-5]) - 1) * 100 if len(close) >= 5 else 0
            
            # 20-day return
            ret_20d = (float(close.iloc[-1]) / float(close.iloc[-20]) - 1) * 100 if len(close) >= 20 else 0
            
            # 50-day high distance (drawdown)
            high50 = float(close.rolling(50, min_periods=1).max().iloc[-1])
            drawdown_from_high = (current - high50) / high50 * 100
            
            results.append({
                'symbol': sym,
                'buy_date': str(buy_date.date()),
                'buy_price': buy_price,
                'sell_price': sell_price,
                'pnl_pct': pnl_pct,
                'win': pnl_pct > 0,
                'rsi_at_entry': rsi,
                'dist_sma20_pct': dist_sma20,
                'ret_5d_pct': ret_5d,
                'ret_20d_pct': ret_20d,
                'drawdown_from_high_pct': drawdown_from_high,
            })
        except Exception as e:
            print("⚠️ [analyze_entry_timing.py] Fallback triggered:", e)

    df_results = pd.DataFrame(results)
    print(f"\n=== Trade Analysis: {len(df_results)} matched trades ===\n")

    if len(df_results) == 0:
        print("No matched trades found.")
        return

    wins = df_results[df_results['win']]
    losses = df_results[~df_results['win']]

    print(f"Win rate: {len(wins)}/{len(df_results)} = {len(wins)/len(df_results)*100:.1f}%")
    print(f"Avg PnL: {df_results['pnl_pct'].mean():.2f}%\n")

    # Key: compare winners vs losers on each entry metric
    metrics = ['rsi_at_entry', 'dist_sma20_pct', 'ret_5d_pct', 'ret_20d_pct', 'drawdown_from_high_pct']

    print("--- Avg at Entry (Winners vs Losers) ---")
    for m in metrics:
        w_avg = wins[m].mean()
        l_avg = losses[m].mean()
        print(f"  {m:35s}: WIN={w_avg:+6.1f}  LOSS={l_avg:+6.1f}  diff={w_avg-l_avg:+6.1f}")

    print("\n--- Overextension Analysis ---")
    bins_dist = [-999, 0, 3, 7, 10, 15, 999]
    labels_dist = ['<0%', '0-3%', '3-7%', '7-10%', '10-15%', '>15%']
    df_results['dist_bin'] = pd.cut(df_results['dist_sma20_pct'], bins=bins_dist, labels=labels_dist)
    grp = df_results.groupby('dist_bin', observed=True).agg(
        count=('win', 'count'),
        win_rate=('win', lambda x: x.mean()*100),
        avg_pnl=('pnl_pct', 'mean')
    ).reset_index()
    print("SMA20 distance at entry vs win rate:")
    print(grp.to_string(index=False))

    print("\n5-day return at entry vs win rate:")
    bins_ret5 = [-999, -5, 0, 5, 10, 15, 999]
    labels_ret5 = ['<-5%', '-5-0%', '0-5%', '5-10%', '10-15%', '>15%']
    df_results['ret5_bin'] = pd.cut(df_results['ret_5d_pct'], bins=bins_ret5, labels=labels_ret5)
    grp2 = df_results.groupby('ret5_bin', observed=True).agg(
        count=('win', 'count'),
        win_rate=('win', lambda x: x.mean()*100),
        avg_pnl=('pnl_pct', 'mean')
    ).reset_index()
    print(grp2.to_string(index=False))

if __name__ == "__main__":
    main()
