"""
10-Year Comparison: Balanced/Defensive Mode vs Aggressive High-Alpha Mode (compare_balanced_vs_aggressive_10y.py)
=================================================================================================================
Compares:
1. Balanced Mode (Current Default): 5 slots (20% each), tight ratchet profit locking.
2. Aggressive High-Alpha Mode: 3 slots (33.3% each), wide trend-following trailing stop (lets runners run to +50%~+100%).
"""

import sys
import math
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
import yfinance as yf
from dataclasses import dataclass
from typing import Dict, List, Tuple

sys.stdout.reconfigure(encoding='utf-8')


@dataclass
class SimResult:
    bot_return_pct: float
    spy_return_pct: float
    qqq_return_pct: float
    mdd_pct: float
    sharpe: float
    win_rate: float
    profit_factor: float
    total_trades: int


class DualMode10YearBacktester:
    def __init__(self):
        self.universe = [
            'NVDA', 'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'TSLA',
            'AMD', 'AVGO', 'LLY', 'ISRG', 'GE', 'CAT', 'LRCX',
            'QCOM', 'JPM', 'UNH', 'NFLX', 'COST', 'CRM'
        ]
        self.benchmarks = ['SPY', 'QQQ']
        self.slippage_pct = 0.0008

    def fetch_10y_data(self) -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
        tickers = self.universe + self.benchmarks
        raw = yf.download(tickers, period='10y', progress=False)
        stock_data, bm_data = {}, {}
        for t in tickers:
            try:
                sub = pd.DataFrame({
                    'Open': raw['Open'][t], 'High': raw['High'][t],
                    'Low': raw['Low'][t], 'Close': raw['Close'][t],
                    'Volume': raw['Volume'][t]
                }).dropna()
                if len(sub) < 100: continue
                sub['SMA20'] = sub['Close'].rolling(20).mean()
                sub['SMA50'] = sub['Close'].rolling(50).mean()
                sub['SMA200'] = sub['Close'].rolling(200).mean()
                tr1 = sub['High'] - sub['Low']
                tr2 = (sub['High'] - sub['Close'].shift(1)).abs()
                tr3 = (sub['Low'] - sub['Close'].shift(1)).abs()
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                sub['ATR'] = tr.rolling(14).mean()
                delta = sub['Close'].diff()
                gain = delta.where(delta > 0, 0.0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
                rs = gain / (loss + 1e-9)
                sub['RSI'] = 100.0 - (100.0 / (1.0 + rs))
                sub['Vol20'] = sub['Volume'].rolling(20).mean()
                sub['RVOL'] = sub['Volume'] / (sub['Vol20'] + 1e-9)
                if t in self.benchmarks: bm_data[t] = sub
                else: stock_data[t] = sub
            except Exception: pass
        return stock_data, bm_data

    def run_simulation(self, stock_data: Dict[str, pd.DataFrame], bm_data: Dict[str, pd.DataFrame],
                       start_date: date, end_date: date, mode: str = "BALANCED") -> SimResult:
        
        spy_df = bm_data['SPY']
        date_mask = (spy_df.index.date >= start_date) & (spy_df.index.date <= end_date)
        sim_dates = [d.date() for d in spy_df.index[date_mask]]
        if not sim_dates:
            return SimResult(0, 0, 0, 0, 0, 0, 0, 0)

        # Mode configuration
        if mode == "AGGRESSIVE":
            max_positions = 3
            slot_pct = 0.333
            initial_stop_pct = 0.940  # -6.0% room for volatility
        else:  # BALANCED
            max_positions = 5
            slot_pct = 0.200
            initial_stop_pct = 0.955  # -4.5% tight stop

        cash = 100_000.0
        positions = {}
        trades = []
        equity_curve = []

        for curr_date in sim_dates:
            closed_symbols = []
            for sym, pos in list(positions.items()):
                df = stock_data.get(sym)
                if df is None or curr_date not in df.index.date: continue
                row = df.loc[df.index.date == curr_date].iloc[0]
                high, low, close = float(row['High']), float(row['Low']), float(row['Close'])
                atr = float(row['ATR']) if not np.isnan(row['ATR']) else close * 0.03

                if high > pos['highest_price']: pos['highest_price'] = high
                max_gain_pct = (pos['highest_price'] / pos['entry_price'] - 1.0) * 100.0
                curr_pnl_pct = (close / pos['entry_price'] - 1.0) * 100.0
                hold_days = (curr_date - pos['entry_date']).days

                if mode == "AGGRESSIVE":
                    # Wide trend-following ratchet: lets big runners go up +50% ~ +100%
                    curr_stop = pos['entry_price'] * initial_stop_pct
                    if max_gain_pct >= 30.0: curr_stop = max(curr_stop, pos['entry_price'] * 1.200)
                    elif max_gain_pct >= 18.0: curr_stop = max(curr_stop, pos['entry_price'] * 1.100)
                    elif max_gain_pct >= 8.0: curr_stop = max(curr_stop, pos['entry_price'] * 1.035)
                    if max_gain_pct >= 6.0: curr_stop = max(curr_stop, pos['highest_price'] - (3.2 * atr))
                else:
                    # Balanced ratchet
                    curr_stop = pos['entry_price'] * initial_stop_pct
                    if max_gain_pct >= 12.0: curr_stop = max(curr_stop, pos['entry_price'] * 1.090)
                    elif max_gain_pct >= 7.0: curr_stop = max(curr_stop, pos['entry_price'] * 1.045)
                    elif max_gain_pct >= 4.0: curr_stop = max(curr_stop, pos['entry_price'] * 1.020)
                    if max_gain_pct >= 3.0: curr_stop = max(curr_stop, pos['highest_price'] - (2.5 * atr))

                pos['stop_price'] = curr_stop
                exit_price = None

                if close <= curr_stop or low <= curr_stop:
                    exit_price = max(curr_stop, low) * (1.0 - self.slippage_pct)
                elif hold_days >= (35 if mode == "AGGRESSIVE" else 20) and curr_pnl_pct < 1.0:
                    exit_price = close * (1.0 - self.slippage_pct)

                if exit_price is not None:
                    pnl = (exit_price - pos['entry_price']) * pos['shares']
                    trades.append(pnl)
                    cash += exit_price * pos['shares']
                    closed_symbols.append(sym)

            for s in closed_symbols: del positions[s]

            open_slots = max_positions - len(positions)
            if open_slots > 0:
                candidates = []
                for sym, df in stock_data.items():
                    if sym in positions or curr_date not in df.index.date: continue
                    hist = df.loc[df.index.date <= curr_date]
                    if len(hist) < 50: continue
                    r_c = hist.iloc[-1]
                    c, sma20, sma50, sma200 = float(r_c['Close']), float(r_c['SMA20']), float(r_c['SMA50']), float(r_c['SMA200'])
                    rsi, rvol, atr = float(r_c['RSI']), float(r_c['RVOL']), float(r_c['ATR']) if not np.isnan(r_c['ATR']) else float(r_c['Close']) * 0.03
                    if not (c >= sma20 * 0.99 and sma20 >= sma50 * 0.98 and c >= sma200 * 0.95): continue
                    if not (45 <= rsi <= 76) or rvol < 1.15: continue
                    p1m = float(hist['Close'].iloc[-21]) if len(hist) >= 21 else c
                    p0 = float(hist['Close'].iloc[0])
                    mom_core = ((c / p0) - 1.0) * 100.0 - ((c / p1m) - 1.0) * 100.0
                    score = (mom_core * 0.4) + (rvol * 25.0) + (100 - abs(rsi - 58))
                    if score >= 65.0: candidates.append((sym, score, c, atr))

                candidates.sort(key=lambda x: x[1], reverse=True)
                for sym, sc, price, atr in candidates[:open_slots]:
                    curr_tot = cash + sum(p['shares'] * float(stock_data[s].loc[stock_data[s].index.date == curr_date]['Close'].iloc[0])
                                          for s, p in positions.items() if curr_date in stock_data[s].index.date)
                    slot_budget = curr_tot * slot_pct
                    allocated_cash = min(cash * 0.95, slot_budget)
                    if allocated_cash < 2000: continue
                    ep = price * (1.0 + self.slippage_pct)
                    sh = int(allocated_cash / ep)
                    if sh > 0:
                        cash -= sh * ep
                        positions[sym] = {'entry_date': curr_date, 'entry_price': ep, 'shares': sh, 'highest_price': ep, 'stop_price': ep * initial_stop_pct}

            pos_val = sum(pos['shares'] * float(stock_data[sym].loc[stock_data[sym].index.date == curr_date]['Close'].iloc[0])
                          for sym, pos in positions.items() if curr_date in stock_data[sym].index.date)
            equity_curve.append((curr_date, cash + pos_val))

        final_equity = equity_curve[-1][1] if equity_curve else 100_000.0
        eq_series = pd.Series([e[1] for e in equity_curve], index=[e[0] for e in equity_curve])
        tot_ret = ((final_equity / 100_000.0) - 1.0) * 100.0
        cum_max = eq_series.cummax()
        mdd = abs(float(((eq_series - cum_max) / cum_max).min())) * 100.0 if len(eq_series) > 0 else 0.0
        daily_rets = eq_series.pct_change().dropna()
        sharpe = (float(daily_rets.mean() * 252) / (float(daily_rets.std() * np.sqrt(252)) + 1e-9)) if len(daily_rets) > 0 else 0.0

        wins = [t for t in trades if t > 0]
        losses = [t for t in trades if t <= 0]
        win_rate = (len(wins) / len(trades) * 100.0) if trades else 0.0
        gross_win = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = (gross_win / gross_loss) if gross_loss > 0 else 1.0

        # Benchmark returns
        spy_sub = bm_data['SPY'].loc[(bm_data['SPY'].index.date >= start_date) & (bm_data['SPY'].index.date <= end_date)]
        qqq_sub = bm_data['QQQ'].loc[(bm_data['QQQ'].index.date >= start_date) & (bm_data['QQQ'].index.date <= end_date)]
        spy_ret = ((float(spy_sub['Close'].iloc[-1]) / float(spy_sub['Close'].iloc[0])) - 1.0) * 100.0 if len(spy_sub) >= 2 else 0.0
        qqq_ret = ((float(qqq_sub['Close'].iloc[-1]) / float(qqq_sub['Close'].iloc[0])) - 1.0) * 100.0 if len(qqq_sub) >= 2 else 0.0

        return SimResult(
            bot_return_pct=round(tot_ret, 2),
            spy_return_pct=round(spy_ret, 2),
            qqq_return_pct=round(qqq_ret, 2),
            mdd_pct=round(mdd, 2),
            sharpe=round(sharpe, 2),
            win_rate=round(win_rate, 2),
            profit_factor=round(profit_factor, 2),
            total_trades=len(trades)
        )


def run_comparison():
    bt = DualMode10YearBacktester()
    print("⏳ Downloading 10-Year Historical Data for Mode Comparison...")
    stocks, benchmarks = bt.fetch_10y_data()

    today = date.today()
    annual_periods = [
        ("1년차 (2016~2017)", date(2016, 8, 15), date(2017, 8, 14)),
        ("2년차 (2017~2018)", date(2017, 8, 15), date(2018, 8, 14)),
        ("3년차 (2018~2019)", date(2018, 8, 15), date(2019, 8, 14)),
        ("4년차 (2019~2020)", date(2019, 8, 15), date(2020, 8, 14)),
        ("5년차 (2020~2021)", date(2020, 8, 15), date(2021, 8, 14)),
        ("6년차 (2021~2022)", date(2021, 8, 15), date(2022, 8, 14)),
        ("7년차 (2022~2023)", date(2022, 8, 15), date(2023, 8, 14)),
        ("8년차 (2023~2024)", date(2023, 8, 15), date(2024, 8, 14)),
        ("9년차 (2024~2025)", date(2024, 8, 15), date(2025, 8, 14)),
        ("10년차(2025~2026)", date(2025, 8, 15), today),
    ]

    print("\n" + "="*125)
    print("🏛️ 10-YEAR DUAL-MODE COMPARISON: BALANCED (DEFENSIVE) vs AGGRESSIVE (HIGH-ALPHA)")
    print("="*125)
    print(f"{'연도 / 기간':<18} | {'안정형 봇':<10} | {'공격형 봇':<10} | {'S&P 500':<10} | {'나스닥 QQQ':<10} | {'안정형 MDD':<10} | {'공격형 MDD':<10} | {'공격형 초과수익':<12}")
    print("-" * 125)

    comp_bal = 100_000.0
    comp_agg = 100_000.0

    for lbl, s_dt, e_dt in annual_periods:
        r_bal = bt.run_simulation(stocks, benchmarks, s_dt, e_dt, mode="BALANCED")
        r_agg = bt.run_simulation(stocks, benchmarks, s_dt, e_dt, mode="AGGRESSIVE")
        comp_bal *= (1.0 + r_bal.bot_return_pct / 100.0)
        comp_agg *= (1.0 + r_agg.bot_return_pct / 100.0)
        diff = r_agg.bot_return_pct - r_bal.bot_return_pct

        print(f"{lbl:<18} | {r_bal.bot_return_pct:>+9.2f}% | {r_agg.bot_return_pct:>+9.2f}% | {r_bal.spy_return_pct:>+9.2f}% | {r_bal.qqq_return_pct:>+9.2f}% | {r_bal.mdd_pct:>9.2f}% | {r_agg.mdd_pct:>9.2f}% | {diff:>+11.2f}%")

    tot_bal = ((comp_bal / 100_000.0) - 1.0) * 100.0
    tot_agg = ((comp_agg / 100_000.0) - 1.0) * 100.0
    cagr_bal = (math.pow(comp_bal / 100_000.0, 1.0 / 10.0) - 1.0) * 100.0
    cagr_agg = (math.pow(comp_agg / 100_000.0, 1.0 / 10.0) - 1.0) * 100.0

    spy_c = benchmarks['SPY']['Close']
    qqq_c = benchmarks['QQQ']['Close']
    tot_spy = ((float(spy_c.iloc[-1]) / float(spy_c.iloc[0])) - 1.0) * 100.0
    tot_qqq = ((float(qqq_c.iloc[-1]) / float(qqq_c.iloc[0])) - 1.0) * 100.0

    print("="*125)
    print(f"📊 [10년 복리 누적 자산 최종 비교 (2016-2026)]")
    print(f"  • S&P 500 (SPY)       :  {tot_spy:>+8.2f}% ($100,000 ➔ ${(100_000*(1+tot_spy/100)):,.2f})")
    print(f"  • Nasdaq 100 (QQQ)     :  {tot_qqq:>+8.2f}% ($100,000 ➔ ${(100_000*(1+tot_qqq/100)):,.2f})")
    print(f"  • 안정형 봇 (Balanced) :  {tot_bal:>+8.2f}% ($100,000 ➔ ${comp_bal:,.2f} | CAGR: {cagr_bal:.2f}%/년)")
    print(f"  • 공격형 봇 (Aggressive): {tot_agg:>+8.2f}% ($100,000 ➔ ${comp_agg:,.2f} | CAGR: {cagr_agg:.2f}%/년 🚀)")
    print("="*125)


if __name__ == "__main__":
    run_comparison()
