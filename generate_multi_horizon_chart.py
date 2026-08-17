import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import date

sys.stdout.reconfigure(encoding='utf-8')

# Run backtest simulation to get daily equity curves
from comprehensive_multi_horizon_backtest import MultiHorizonBacktester
bt = MultiHorizonBacktester(initial_capital=100_000.0)
stocks, benchmarks = bt.fetch_all_data()

# 2-Year simulation
start_dt = date(2024, 8, 15)
end_dt = date.today()

# Get benchmark prices
spy_c = benchmarks['SPY'].loc[(benchmarks['SPY'].index.date >= start_dt) & (benchmarks['SPY'].index.date <= end_dt)]['Close']
qqq_c = benchmarks['QQQ'].loc[(benchmarks['QQQ'].index.date >= start_dt) & (benchmarks['QQQ'].index.date <= end_dt)]['Close']
iwm_c = benchmarks['IWM'].loc[(benchmarks['IWM'].index.date >= start_dt) & (benchmarks['IWM'].index.date <= end_dt)]['Close']

spy_norm = (spy_c / spy_c.iloc[0] - 1.0) * 100.0
qqq_norm = (qqq_c / qqq_c.iloc[0] - 1.0) * 100.0
iwm_norm = (iwm_c / iwm_c.iloc[0] - 1.0) * 100.0

# 1. 2-Year Equity Curve
sim_dates = [d.date() for d in benchmarks['SPY'].index[(benchmarks['SPY'].index.date >= start_dt) & (benchmarks['SPY'].index.date <= end_dt)]]

cash = 100_000.0
positions = {}
eq_curve = []
slippage_pct = 0.0008

for curr_date in sim_dates:
    closed = []
    for sym, pos in list(positions.items()):
        df = stocks.get(sym)
        if df is None or curr_date not in df.index.date:
            continue
        row = df.loc[df.index.date == curr_date].iloc[0]
        h, l, c, atr = float(row['High']), float(row['Low']), float(row['Close']), float(row['ATR']) if not np.isnan(row['ATR']) else float(row['Close']) * 0.03
        if h > pos['highest_price']: pos['highest_price'] = h
        max_g = (pos['highest_price'] / pos['entry_price'] - 1.0) * 100.0
        hold_d = (curr_date - pos['entry_date']).days
        stop = pos['entry_price'] * 0.955
        if max_g >= 12.0: stop = max(stop, pos['entry_price'] * 1.090)
        elif max_g >= 7.0: stop = max(stop, pos['entry_price'] * 1.045)
        elif max_g >= 4.0: stop = max(stop, pos['entry_price'] * 1.020)
        if max_g >= 3.0: stop = max(stop, pos['highest_price'] - 2.5 * atr)
        if l <= stop or c <= stop or (hold_d >= 20 and (c/pos['entry_price']-1.0)*100 < 1.0):
            ex_p = max(stop, l) * (1.0 - slippage_pct)
            cash += ex_p * pos['shares']
            closed.append(sym)
    for s in closed: del positions[s]

    slots = 5 - len(positions)
    if slots > 0:
        cands = []
        for sym, df in stocks.items():
            if sym in positions or curr_date not in df.index.date: continue
            hist = df.loc[df.index.date <= curr_date]
            if len(hist) < 50: continue
            r_c = hist.iloc[-1]
            c, sma20, sma50, sma200 = float(r_c['Close']), float(r_c['SMA20']), float(r_c['SMA50']), float(r_c['SMA200'])
            rsi, rvol, atr = float(r_c['RSI']), float(r_c['RVOL']), float(r_c['ATR']) if not np.isnan(r_c['ATR']) else float(r_c['Close']) * 0.03
            if not (c >= sma20 * 0.99 and sma20 >= sma50 * 0.98 and c >= sma200 * 0.95): continue
            if not (45 <= rsi <= 74) or rvol < 1.15: continue
            p1m = float(hist['Close'].iloc[-21]) if len(hist) >= 21 else c
            p0 = float(hist['Close'].iloc[0])
            score = (((c/p0-1)*100 - (c/p1m-1)*100) * 0.4) + (rvol * 25.0) + (100 - abs(rsi - 58))
            if score >= 65: cands.append((sym, score, c, atr))
        cands.sort(key=lambda x: x[1], reverse=True)
        for sym, sc, p, atr in cands[:slots]:
            curr_eq = cash + sum(pos['shares'] * float(stocks[s].loc[stocks[s].index.date == curr_date]['Close'].iloc[0]) for s, pos in positions.items() if curr_date in stocks[s].index.date)
            bud = curr_eq * 0.20
            alloc = min(cash * 0.95, bud)
            if alloc < 2000: continue
            ep = p * (1.0 + slippage_pct)
            sh = int(alloc / ep)
            if sh > 0:
                cash -= sh * ep
                positions[sym] = {'entry_date': curr_date, 'entry_price': ep, 'shares': sh, 'highest_price': ep, 'stop_price': ep * 0.955}
    pv = sum(pos['shares'] * float(stocks[s].loc[stocks[s].index.date == curr_date]['Close'].iloc[0]) for s, pos in positions.items() if curr_date in stocks[s].index.date)
    eq_curve.append((curr_date, cash + pv))

# Format DataFrame
eq_df = pd.DataFrame(eq_curve, columns=['Date', 'Equity']).set_index('Date')
eq_norm = (eq_df['Equity'] / eq_df['Equity'].iloc[0] - 1.0) * 100.0

# Plotting 2-Panel Chart (Cumulative Returns & Drawdown)
plt.style.use('dark_background')
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9), gridspec_kw={'height_ratios': [3, 1.2]}, sharex=True)

# Panel 1: Cumulative Return %
ax1.plot(eq_df.index, eq_norm, label=f'KIS Quant Bot (+{eq_norm.iloc[-1]:.1f}%)', color='#00FFCC', linewidth=2.5)
ax1.plot(spy_norm.index.date, spy_norm, label=f'S&P 500 SPY (+{spy_norm.iloc[-1]:.1f}%)', color='#FFB800', linestyle='--', linewidth=1.8, alpha=0.85)
ax1.plot(qqq_norm.index.date, qqq_norm, label=f'Nasdaq 100 QQQ (+{qqq_norm.iloc[-1]:.1f}%)', color='#FF3366', linestyle=':', linewidth=1.8, alpha=0.85)
ax1.plot(iwm_norm.index.date, iwm_norm, label=f'Russell 2000 IWM (+{iwm_norm.iloc[-1]:.1f}%)', color='#9966FF', linestyle='-.', linewidth=1.5, alpha=0.75)

ax1.set_title('Institutional Walk-Forward Multi-Horizon Backtest vs Major Benchmarks (2024-2026)', fontsize=15, fontweight='bold', color='white', pad=15)
ax1.set_ylabel('Cumulative Return (%)', fontsize=12, fontweight='bold', color='white')
ax1.grid(True, linestyle='--', alpha=0.25)
ax1.legend(loc='upper left', fontsize=11, framealpha=0.6)

# Panel 2: Drawdown %
bot_dd = (eq_df['Equity'] - eq_df['Equity'].cummax()) / eq_df['Equity'].cummax() * 100.0
spy_dd = (spy_c - spy_c.cummax()) / spy_c.cummax() * 100.0

ax2.fill_between(eq_df.index, bot_dd, 0, color='#00FFCC', alpha=0.4, label=f'Bot MDD ({bot_dd.min():.1f}%)')
ax2.plot(spy_norm.index.date, spy_dd, color='#FFB800', linestyle='--', linewidth=1.2, alpha=0.8, label=f'SPY MDD ({spy_dd.min():.1f}%)')
ax2.set_ylabel('Drawdown (%)', fontsize=11, fontweight='bold', color='white')
ax2.set_xlabel('Date', fontsize=11, fontweight='bold', color='white')
ax2.grid(True, linestyle='--', alpha=0.25)
ax2.legend(loc='lower left', fontsize=10, framealpha=0.6)

plt.tight_layout()

# Save to artifacts
target_path = r'C:\Users\wngud\.gemini\antigravity\brain\2428f2be-2492-4671-a2b2-dffa00220c1c\multi_horizon_backtest_chart.png'
plt.savefig(target_path, dpi=180)
print(f'✅ Chart successfully saved to {target_path}')
