"""
10-Year Institutional Annual Breakdown Backtest Engine (backtest_10years_annual_breakdown.py)
=============================================================================================
Performs an exhaustive 10-Year (2016-2026) bar-by-bar walk-forward simulation
broken down into 10 distinct 1-year periods:
- Covers Bull markets, Fed Rate Hikes (2018, 2022), COVID Crash (2020), and AI Boom (2023-2026).
- Compares each year against S&P 500 (SPY) and Nasdaq 100 (QQQ).
- Zero database write (100% In-Memory Isolation).
- 0.08% Roundtrip Slippage & Commission deduction.
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
class TradeRecord:
    symbol: str
    entry_date: date
    entry_price: float
    exit_date: date
    exit_price: float
    pnl: float
    pnl_pct: float
    hold_days: int
    exit_reason: str


class TenYearAnnualBacktester:
    def __init__(self, initial_capital: float = 100_000.0, max_positions: int = 5):
        self.initial_capital = initial_capital
        self.max_positions = max_positions
        self.slot_pct = 1.0 / max_positions
        self.slippage_pct = 0.0008

        self.universe = [
            'NVDA', 'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'TSLA',
            'AMD', 'AVGO', 'LLY', 'ISRG', 'GE', 'CAT', 'LRCX',
            'QCOM', 'JPM', 'UNH', 'NFLX', 'COST', 'CRM'
        ]
        self.benchmarks = ['SPY', 'QQQ']

    def fetch_10y_data(self) -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
        tickers = self.universe + self.benchmarks
        raw = yf.download(tickers, period='10y', progress=False)
        
        stock_data = {}
        bm_data = {}

        for t in tickers:
            try:
                sub = pd.DataFrame({
                    'Open': raw['Open'][t],
                    'High': raw['High'][t],
                    'Low': raw['Low'][t],
                    'Close': raw['Close'][t],
                    'Volume': raw['Volume'][t]
                }).dropna()

                if len(sub) < 100:
                    continue

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

                if t in self.benchmarks:
                    bm_data[t] = sub
                else:
                    stock_data[t] = sub
            except Exception:
                pass

        return stock_data, bm_data

    def run_period(self, stock_data: Dict[str, pd.DataFrame], bm_data: Dict[str, pd.DataFrame],
                   start_date: date, end_date: date, starting_cash: float = 100_000.0) -> dict:
        
        spy_df = bm_data['SPY']
        date_mask = (spy_df.index.date >= start_date) & (spy_df.index.date <= end_date)
        sim_dates = [d.date() for d in spy_df.index[date_mask]]

        if not sim_dates:
            return {}

        cash = starting_cash
        positions = {}
        trades: List[TradeRecord] = []
        equity_curve = []

        for curr_date in sim_dates:
            # 1. Update existing positions & check exits
            closed_symbols = []
            for sym, pos in list(positions.items()):
                df = stock_data.get(sym)
                if df is None or curr_date not in df.index.date:
                    continue

                row = df.loc[df.index.date == curr_date].iloc[0]
                high, low, close = float(row['High']), float(row['Low']), float(row['Close'])
                atr = float(row['ATR']) if not np.isnan(row['ATR']) else close * 0.03

                if high > pos['highest_price']:
                    pos['highest_price'] = high

                max_gain_pct = (pos['highest_price'] / pos['entry_price'] - 1.0) * 100.0
                curr_pnl_pct = (close / pos['entry_price'] - 1.0) * 100.0
                hold_days = (curr_date - pos['entry_date']).days

                # Dynamic Ratchet Stop
                curr_stop = pos['entry_price'] * 0.955
                if max_gain_pct >= 12.0:
                    curr_stop = max(curr_stop, pos['entry_price'] * 1.090)
                elif max_gain_pct >= 7.0:
                    curr_stop = max(curr_stop, pos['entry_price'] * 1.045)
                elif max_gain_pct >= 4.0:
                    curr_stop = max(curr_stop, pos['entry_price'] * 1.020)

                # Chandelier Trailing Stop
                if max_gain_pct >= 3.0:
                    curr_stop = max(curr_stop, pos['highest_price'] - (2.5 * atr))

                pos['stop_price'] = curr_stop

                exit_price = None
                exit_reason = None

                if close <= curr_stop or low <= curr_stop:
                    exit_price = max(curr_stop, low) * (1.0 - self.slippage_pct)
                    exit_reason = "PROFIT_LOCK_RATCHET" if curr_stop > pos['entry_price'] else "INITIAL_STOP_LOSS"
                elif hold_days >= 20 and curr_pnl_pct < 1.0:
                    exit_price = close * (1.0 - self.slippage_pct)
                    exit_reason = "STAGNATION_TIME_DECAY"

                if exit_price is not None:
                    pnl = (exit_price - pos['entry_price']) * pos['shares']
                    pnl_pct = (exit_price / pos['entry_price'] - 1.0) * 100.0
                    trades.append(TradeRecord(
                        symbol=sym,
                        entry_date=pos['entry_date'],
                        entry_price=pos['entry_price'],
                        exit_date=curr_date,
                        exit_price=exit_price,
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        hold_days=hold_days,
                        exit_reason=exit_reason
                    ))
                    cash += exit_price * pos['shares']
                    closed_symbols.append(sym)

            for sym in closed_symbols:
                del positions[sym]

            # 2. Check Entries
            open_slots = self.max_positions - len(positions)
            if open_slots > 0:
                candidates = []
                for sym, df in stock_data.items():
                    if sym in positions or curr_date not in df.index.date:
                        continue

                    hist = df.loc[df.index.date <= curr_date]
                    if len(hist) < 50:
                        continue

                    r_curr = hist.iloc[-1]
                    c = float(r_curr['Close'])
                    sma20 = float(r_curr['SMA20']) if not np.isnan(r_curr['SMA20']) else c
                    sma50 = float(r_curr['SMA50']) if not np.isnan(r_curr['SMA50']) else c
                    sma200 = float(r_curr['SMA200']) if not np.isnan(r_curr['SMA200']) else c
                    rsi = float(r_curr['RSI']) if not np.isnan(r_curr['RSI']) else 50
                    rvol = float(r_curr['RVOL']) if not np.isnan(r_curr['RVOL']) else 1.0
                    atr = float(r_curr['ATR']) if not np.isnan(r_curr['ATR']) else c * 0.03

                    # Quantitative Filter matching live strategy
                    if not (c >= sma20 * 0.99 and sma20 >= sma50 * 0.98 and c >= sma200 * 0.95):
                        continue
                    if not (45 <= rsi <= 74) or rvol < 1.15:
                        continue

                    p_1m = float(hist['Close'].iloc[-21]) if len(hist) >= 21 else c
                    p_start = float(hist['Close'].iloc[0])
                    mom_12m = ((c / p_start) - 1.0) * 100.0
                    mom_1m = ((c / p_1m) - 1.0) * 100.0
                    mom_core = mom_12m - mom_1m

                    score = (mom_core * 0.4) + (rvol * 25.0) + (100 - abs(rsi - 58))
                    if score >= 65.0:
                        candidates.append((sym, score, c, atr))

                candidates.sort(key=lambda x: x[1], reverse=True)

                for sym, sc, price, atr in candidates[:open_slots]:
                    curr_tot = cash + sum(p['shares'] * float(stock_data[s].loc[stock_data[s].index.date == curr_date]['Close'].iloc[0])
                                          for s, p in positions.items() if curr_date in stock_data[s].index.date)
                    slot_budget = curr_tot * self.slot_pct
                    allocated_cash = min(cash * 0.95, slot_budget)
                    if allocated_cash < 2000:
                        continue

                    exec_price = price * (1.0 + self.slippage_pct)
                    shares = int(allocated_cash / exec_price)
                    if shares > 0:
                        cost = shares * exec_price
                        cash -= cost
                        positions[sym] = {
                            'entry_date': curr_date,
                            'entry_price': exec_price,
                            'shares': shares,
                            'highest_price': exec_price,
                            'stop_price': exec_price * 0.955
                        }

            # 3. Daily Portfolio Valuation
            pos_val = sum(pos['shares'] * float(stock_data[sym].loc[stock_data[sym].index.date == curr_date]['Close'].iloc[0])
                          for sym, pos in positions.items() if curr_date in stock_data[sym].index.date)
            equity_curve.append((curr_date, cash + pos_val))

        final_equity = equity_curve[-1][1] if equity_curve else starting_cash
        eq_series = pd.Series([e[1] for e in equity_curve], index=[e[0] for e in equity_curve])
        tot_ret_pct = ((final_equity / starting_cash) - 1.0) * 100.0

        # Drawdown
        cum_max = eq_series.cummax()
        drawdowns = (eq_series - cum_max) / cum_max
        mdd_pct = abs(float(drawdowns.min())) * 100.0 if len(drawdowns) > 0 else 0.0

        # Sharpe
        daily_rets = eq_series.pct_change().dropna()
        sharpe = (float(daily_rets.mean() * 252) / (float(daily_rets.std() * np.sqrt(252)) + 1e-9)) if len(daily_rets) > 0 else 0.0

        # Win Rate & PF
        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]
        win_rate = (len(wins) / len(trades) * 100.0) if trades else 0.0
        gross_win = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        profit_factor = (gross_win / gross_loss) if gross_loss > 0 else (99.0 if gross_win > 0 else 1.0)

        # Benchmark calculations
        bm_rets = {}
        bm_mdds = {}
        for bm in self.benchmarks:
            df = bm_data[bm]
            bm_sub = df.loc[(df.index.date >= start_date) & (df.index.date <= end_date)]
            if len(bm_sub) >= 2:
                r = ((float(bm_sub['Close'].iloc[-1]) / float(bm_sub['Close'].iloc[0])) - 1.0) * 100.0
                bm_rets[bm] = round(r, 2)
                c = bm_sub['Close']
                dd = (c - c.cummax()) / c.cummax()
                bm_mdds[bm] = round(abs(float(dd.min())) * 100.0, 2)
            else:
                bm_rets[bm] = 0.0
                bm_mdds[bm] = 0.0

        return {
            'start_date': start_date,
            'end_date': end_date,
            'starting_cash': starting_cash,
            'final_equity': round(final_equity, 2),
            'bot_return_pct': round(tot_ret_pct, 2),
            'spy_return_pct': bm_rets.get('SPY', 0.0),
            'qqq_return_pct': bm_rets.get('QQQ', 0.0),
            'alpha_vs_spy': round(tot_ret_pct - bm_rets.get('SPY', 0.0), 2),
            'alpha_vs_qqq': round(tot_ret_pct - bm_rets.get('QQQ', 0.0), 2),
            'bot_mdd_pct': round(mdd_pct, 2),
            'spy_mdd_pct': bm_mdds.get('SPY', 0.0),
            'qqq_mdd_pct': bm_mdds.get('QQQ', 0.0),
            'sharpe': round(sharpe, 2),
            'win_rate': round(win_rate, 2),
            'profit_factor': round(profit_factor, 2),
            'total_trades': len(trades),
            'win_trades': len(wins),
            'loss_trades': len(losses)
        }


def run_10year_annual_analysis():
    bt = TenYearAnnualBacktester(initial_capital=100_000.0)
    print("⏳ Downloading 10-Year Historical Data (2016 - 2026)...")
    stocks, benchmarks = bt.fetch_10y_data()

    # Define 10 Annual Periods
    annual_periods = [
        ("Year 1  (2016.08 ~ 2017.08)", date(2016, 8, 15), date(2017, 8, 14), "Post-Election Trump Rally"),
        ("Year 2  (2017.08 ~ 2018.08)", date(2017, 8, 15), date(2018, 8, 14), "Tax Cuts & Corporate Earnings Boom"),
        ("Year 3  (2018.08 ~ 2019.08)", date(2018, 8, 15), date(2019, 8, 14), "Q4 2018 Trade War & Fed Hike Crash"),
        ("Year 4  (2019.08 ~ 2020.08)", date(2019, 8, 15), date(2020, 8, 14), "COVID-19 Flash Crash & Tech Explosion"),
        ("Year 5  (2020.08 ~ 2021.08)", date(2020, 8, 15), date(2021, 8, 14), "Zero Rates & Quantitative Easing Mania"),
        ("Year 6  (2021.08 ~ 2022.08)", date(2021, 8, 15), date(2022, 8, 14), "Inflation Shock & Tech Bear Market"),
        ("Year 7  (2022.08 ~ 2023.08)", date(2022, 8, 15), date(2023, 8, 14), "Fed 500bp Hikes & Generative AI Onset"),
        ("Year 8  (2023.08 ~ 2024.08)", date(2023, 8, 15), date(2024, 8, 14), "Magnificent 7 AI Infrastructure Expansion"),
        ("Year 9  (2024.08 ~ 2025.08)", date(2024, 8, 15), date(2025, 8, 14), "Fed Rate Cut Pivot & Market Broadening"),
        ("Year 10 (2025.08 ~ 2026.08)", date(2025, 8, 15), date.today(), "Current Active High-Momentum Regime"),
    ]

    print("\n=========================================================================================================================")
    print("🏛️ 10-YEAR (2016-2026) ANNUAL WALK-FORWARD PERFORMANCE REPORT (VS SPY & QQQ)")
    print("=========================================================================================================================")
    print(f"{'Year / Market Regime':<40} | {'Bot Return':<10} | {'SPY Return':<10} | {'QQQ Return':<10} | {'Bot Alpha':<9} | {'Bot MDD':<7} | {'SPY MDD':<7} | {'WinRate':<7} | {'PF':<5}")
    print("-" * 121)

    yearly_results = []
    compounded_capital = 100_000.0

    for label, s_dt, e_dt, theme in annual_periods:
        res = bt.run_period(stocks, benchmarks, s_dt, e_dt, starting_cash=100_000.0)
        yearly_results.append((label, theme, res))
        compounded_capital *= (1.0 + res['bot_return_pct'] / 100.0)
        
        print(f"{label:<40} | {res['bot_return_pct']:>+9.2f}% | {res['spy_return_pct']:>+9.2f}% | {res['qqq_return_pct']:>+9.2f}% | {res['alpha_vs_spy']:>+8.2f}% | {res['bot_mdd_pct']:>6.2f}% | {res['spy_mdd_pct']:>6.2f}% | {res['win_rate']:>6.1f}% | {res['profit_factor']:>5.2f}")

    # 10-Year Cumulative Compound Statistics
    tot_10y_return_pct = ((compounded_capital / 100_000.0) - 1.0) * 100.0
    cagr = (math.pow(compounded_capital / 100_000.0, 1.0 / 10.0) - 1.0) * 100.0

    spy_10y_c = benchmarks['SPY']['Close']
    qqq_10y_c = benchmarks['QQQ']['Close']
    spy_10y_tot = ((float(spy_10y_c.iloc[-1]) / float(spy_10y_c.iloc[0])) - 1.0) * 100.0
    qqq_10y_tot = ((float(qqq_10y_c.iloc[-1]) / float(qqq_10y_c.iloc[0])) - 1.0) * 100.0

    print("=========================================================================================================================")
    print(f"📊 [10-YEAR COMPOUNDED ACCUMULATIVE RESULTS (2016-2026)]")
    print(f"  • Bot 10-Year Compounded Total Return : {tot_10y_return_pct:>+8.2f}% ($100,000 ➔ ${compounded_capital:,.2f})")
    print(f"  • S&P 500 (SPY) 10-Year Total Return   : {spy_10y_tot:>+8.2f}%")
    print(f"  • Nasdaq 100 (QQQ) 10-Year Total Return: {qqq_10y_tot:>+8.2f}%")
    print(f"  • Bot Annual Compound Growth (CAGR)   : {cagr:>8.2f}% per year")
    print("=========================================================================================================================")


if __name__ == "__main__":
    run_10year_annual_analysis()
