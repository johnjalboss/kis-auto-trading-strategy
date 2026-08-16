"""
backtest_multi_timeframe.py
================================================================================
Comprehensive Multi-Timeframe Quantitative Backtester
- Compares AI Quant Strategy vs SPY & QQQ across 5 Time Horizons:
  1. 단기 (1 Month / 20 Trading Days)
  2. 중단기 (3 Months / 65 Trading Days)
  3. 중기 (6 Months / 130 Trading Days)
  4. 중장기 (1 Year / 252 Trading Days)
  5. 장기 (3 Years / 756 Trading Days)
- Computes:
  - Total Return (%) vs SPY vs QQQ
  - Alpha (%p), Win Rate (%), Profit Factor, Max Drawdown (MDD %)
  - Sharpe Ratio, Sortino Ratio, Avg Hold Days, Calmar Ratio
================================================================================
"""

import os
import sys
import io
import datetime
import numpy as np
import pandas as pd
import yfinance as yf
from typing import Dict, List, Any, Tuple

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

TIMEFRAMES = [
    {"name": "단기 (1개월)", "days": 30, "label": "1M"},
    {"name": "중단기 (3개월)", "days": 90, "label": "3M"},
    {"name": "중기 (6개월)", "days": 180, "label": "6M"},
    {"name": "중장기 (1년)", "days": 365, "label": "1Y"},
    {"name": "장기 (3년)", "days": 1095, "label": "3Y"}
]

# Core universe of diversified theme leaders and liquid US equities
BACKTEST_UNIVERSE = [
    # AI / Semi
    "NVDA", "AVGO", "AMD", "MRVL", "TSM", "ARM", "QCOM", "AMAT",
    # Big Tech / Cloud / Platform
    "MSFT", "AAPL", "GOOGL", "AMZN", "META", "PLTR",
    # Energy / Nuclear / Clean Power
    "VST", "CEG", "GEV", "TLN", "NRG", "FSLR", "OKLO", "SMR",
    # Defense / Drones / Aerospace
    "KTOS", "AVAV", "RTX", "LMT", "GD", "NOC", "LDOS", "RCAT",
    # Bio / Pharma / GLP-1
    "LLY", "NVO", "MRK", "ABBV", "AMGN", "VRTX", "ISRG",
    # Financials / Crypto / Fintech
    "JPM", "GS", "MS", "COIN", "MSTR", "HOOD", "XYZ",
    # Industrial / Robotics / Auto / Hardware
    "TSLA", "SYM", "UBER", "DE", "CAT", "ETN", "PH",
    # Materials / Rare Earth / Critical Minerals
    "MP", "FCX", "NEM", "ALB"
]

def fetch_historical_dataset(symbols: List[str], max_days: int = 1150) -> Dict[str, pd.DataFrame]:
    """Downloads historical daily OHLCV for universe and benchmarks."""
    all_syms = list(dict.fromkeys(symbols + ["SPY", "QQQ"]))
    print(f"Downloading historical data for {len(all_syms)} tickers (up to 3 years)...")
    tickers_str = " ".join(all_syms)
    raw = yf.download(tickers_str, period="3y", interval="1d", progress=False, group_by="ticker", auto_adjust=True)
    
    data_dict = {}
    for s in all_syms:
        try:
            if s in raw.columns.levels[0]:
                df = raw[s].dropna()
                if len(df) >= 20:
                    data_dict[s] = df
        except Exception:
            pass
    print(f"Successfully loaded {len(data_dict)} tickers with valid history.")
    return data_dict

def run_simulation(data_dict: Dict[str, pd.DataFrame], days_back: int) -> Dict[str, Any]:
    """
    Executes an event-driven backtest simulation for a specific historical window.
    """
    spy_df = data_dict.get("SPY")
    qqq_df = data_dict.get("QQQ")
    if spy_df is None or len(spy_df) < 20:
        return {}

    # Slice historical window
    if len(spy_df) < days_back:
        window_spy = spy_df
    else:
        window_spy = spy_df.iloc[-days_back:]

    start_date = window_spy.index[0]
    end_date = window_spy.index[-1]
    trading_days = len(window_spy)

    # Benchmark Returns
    spy_start = float(window_spy['Close'].iloc[0])
    spy_end = float(window_spy['Close'].iloc[-1])
    spy_return = ((spy_end / spy_start) - 1.0) * 100.0

    qqq_return = 0.0
    if qqq_df is not None:
        w_qqq = qqq_df.loc[qqq_df.index >= start_date]
        if len(w_qqq) >= 2:
            qqq_return = ((float(w_qqq['Close'].iloc[-1]) / float(w_qqq['Close'].iloc[0])) - 1.0) * 100.0

    # Simulation State
    INITIAL_CAPITAL = 10000.0
    cash = INITIAL_CAPITAL
    MAX_POSITIONS = 5
    SLIPPAGE_PCT = 0.0005  # 0.05% slippage

    positions = {}  # {symbol: {qty, entry_price, highest_price, stop_loss, target_price, atr, entry_date}}
    trades = []     # [{symbol, pnl, pnl_pct, hold_days, reason}]
    equity_curve = []

    # Get trading calendar dates
    date_series = window_spy.index

    for current_idx, current_date in enumerate(date_series):
        # 0. Market Regime Filter (SPY Trend & Volatility Protection)
        spy_slice = spy_df.loc[:current_date]
        spy_c = spy_slice['Close']
        spy_ma50 = float(spy_c.tail(50).mean()) if len(spy_c) >= 50 else float(spy_c.iloc[-1])
        spy_curr = float(spy_c.iloc[-1])
        is_bull_regime = (spy_curr >= spy_ma50 * 0.985)  # Defensive threshold
        
        # 1. Update Open Positions & Check Exits
        symbols_to_close = []
        for sym, pos in list(positions.items()):
            df_s = data_dict.get(sym)
            if df_s is None or current_date not in df_s.index:
                continue

            row = df_s.loc[current_date]
            curr_close = float(row['Close'])
            curr_high = float(row['High'])
            curr_low = float(row['Low'])

            entry_p = pos['entry_price']
            highest_p = max(pos['highest_price'], curr_high)
            pos['highest_price'] = highest_p

            peak_gain_pct = ((highest_p / entry_p) - 1.0) * 100.0
            curr_gain_pct = ((curr_close / entry_p) - 1.0) * 100.0
            atr = pos['atr']

            # Dynamic Chandelier Trailing Stop
            effective_stop = pos['stop_loss']
            if peak_gain_pct >= 6.0:
                chandelier_stop = highest_p - (2.0 * atr)
                if peak_gain_pct >= 20.0:
                    ratchet_floor = entry_p * 1.12
                elif peak_gain_pct >= 12.0:
                    ratchet_floor = entry_p * 1.06
                else:
                    ratchet_floor = entry_p * 1.025
                effective_stop = max(chandelier_stop, ratchet_floor, pos['stop_loss'])

            # Market Regime Breakdown Emergency Exit
            if not is_bull_regime and curr_gain_pct < 0:
                effective_stop = max(effective_stop, curr_close)

            if curr_low <= effective_stop:
                exit_price = min(curr_close, effective_stop) * (1.0 - SLIPPAGE_PCT)
                exit_reason = "TRAILING_STOP" if peak_gain_pct >= 6.0 else "STOP_LOSS"
                symbols_to_close.append((sym, exit_price, exit_reason))
            elif curr_high >= pos['target_price'] and peak_gain_pct < 6.0:
                exit_price = pos['target_price'] * (1.0 - SLIPPAGE_PCT)
                exit_reason = "TARGET_PROFIT"
                symbols_to_close.append((sym, exit_price, exit_reason))
            elif (current_date - pos['entry_date']).days > 35:  # Maximum hold swing window
                exit_price = curr_close * (1.0 - SLIPPAGE_PCT)
                exit_reason = "TIME_EXPIRY"
                symbols_to_close.append((sym, exit_price, exit_reason))

        for sym, exit_p, reason in symbols_to_close:
            pos = positions.pop(sym)
            trade_pnl = (exit_p - pos['entry_price']) * pos['qty']
            trade_pct = ((exit_p / pos['entry_price']) - 1.0) * 100.0
            cash += (exit_p * pos['qty'])
            hold_days = (current_date - pos['entry_date']).days
            trades.append({
                "symbol": sym, "pnl": trade_pnl, "pnl_pct": trade_pct,
                "hold_days": hold_days, "reason": reason
            })

        # 2. Check New Entries (Only in Bullish / Healthy Market Regimes)
        available_slots = MAX_POSITIONS - len(positions)
        if available_slots > 0 and is_bull_regime and current_idx < len(date_series) - 1:
            candidates = []
            for sym, df_s in data_dict.items():
                if sym in ["SPY", "QQQ"] or sym in positions:
                    continue
                if current_date not in df_s.index:
                    continue

                hist_slice = df_s.loc[:current_date]
                if len(hist_slice) < 65:
                    continue

                c_vals = hist_slice['Close']
                v_vals = hist_slice['Volume']
                curr_p = float(c_vals.iloc[-1])
                if curr_p < 5.0:
                    continue

                # Relative Strength vs SPY (12M & 3M Momentum)
                ret_5d = float((curr_p / c_vals.iloc[-6] - 1.0) * 100.0) if len(c_vals) >= 6 else 0.0
                ret_20d = float((curr_p / c_vals.iloc[-21] - 1.0) * 100.0) if len(c_vals) >= 21 else 0.0
                ret_60d = float((curr_p / c_vals.iloc[-61] - 1.0) * 100.0) if len(c_vals) >= 61 else 0.0

                ma20 = float(c_vals.tail(20).mean())
                ma50 = float(c_vals.tail(50).mean())
                is_aligned = (curr_p > ma20 > ma50)

                # High Volume Expansion
                med_v20 = float(v_vals.tail(20).median())
                rvol = float(v_vals.iloc[-1] / med_v20) if med_v20 > 0 else 1.0

                # 52-Week High Proximity
                high_52w = float(hist_slice['High'].tail(252).max()) if len(hist_slice) >= 252 else float(hist_slice['High'].max())
                dist_52w = curr_p / high_52w if high_52w > 0 else 1.0

                # ATR-14 Volatility
                h_vals = hist_slice['High']
                l_vals = hist_slice['Low']
                tr = np.maximum(h_vals.iloc[-14:] - l_vals.iloc[-14:],
                                np.abs(h_vals.iloc[-14:] - c_vals.iloc[-15:-1].values))
                atr_14 = float(np.mean(tr)) if len(tr) > 0 else curr_p * 0.025
                atr_pct = (atr_14 / curr_p) * 100.0

                # Institutional Alpha Leader Score (100 pts)
                score = 0
                if 1.5 <= ret_5d <= 6.5: score += 30
                elif 0.0 <= ret_5d < 1.5: score += 15
                elif ret_5d > 6.5: score += 10

                if ret_20d >= 3.0: score += 25
                elif 0.0 <= ret_20d < 3.0: score += 15

                if ret_60d >= 8.0: score += 20
                elif 0.0 <= ret_60d < 8.0: score += 10

                if rvol >= 1.2: score += 15
                elif rvol >= 0.8: score += 8

                if is_aligned: score += 10
                if dist_52w >= 0.85: score += 10  # Leader trading near 52W High

                if score >= 75 and is_aligned and dist_52w >= 0.82:
                    candidates.append({
                        "symbol": sym, "score": score, "price": curr_p, "atr": atr_14, "atr_pct": atr_pct, "ret_20d": ret_20d
                    })

            candidates.sort(key=lambda x: (x['score'], x['ret_20d']), reverse=True)
            for cand in candidates[:available_slots]:
                alloc_capital = (cash / (available_slots + 1)) * 0.95
                if alloc_capital >= 500:
                    buy_price = cand['price'] * (1.0 + SLIPPAGE_PCT)
                    qty = int(alloc_capital / buy_price)
                    if qty > 0:
                        stop_pct = max(3.0, min(6.5, cand['atr_pct'] * 1.5))
                        target_pct = max(8.0, min(28.0, cand['atr_pct'] * 4.5))

                        positions[cand['symbol']] = {
                            "qty": qty,
                            "entry_price": buy_price,
                            "highest_price": buy_price,
                            "stop_loss": buy_price * (1.0 - stop_pct / 100.0),
                            "target_price": buy_price * (1.0 + target_pct / 100.0),
                            "atr": cand['atr'],
                            "entry_date": current_date
                        }
                        cash -= (buy_price * qty)
                        available_slots -= 1

        # Track Total Equity
        open_val = 0.0
        for sym, pos in positions.items():
            df_s = data_dict.get(sym)
            if df_s is not None and current_date in df_s.index:
                open_val += float(df_s.loc[current_date]['Close']) * pos['qty']
            else:
                open_val += pos['entry_price'] * pos['qty']

        current_total_equity = cash + open_val
        equity_curve.append(current_total_equity)

    # Performance Metrics
    final_equity = equity_curve[-1] if equity_curve else INITIAL_CAPITAL
    strategy_return = ((final_equity / INITIAL_CAPITAL) - 1.0) * 100.0
    alpha_spy = strategy_return - spy_return
    alpha_qqq = strategy_return - qqq_return

    # Max Drawdown
    eq_series = pd.Series(equity_curve)
    cummax = eq_series.cummax()
    drawdown = (eq_series - cummax) / cummax * 100.0
    mdd = abs(float(drawdown.min())) if len(drawdown) > 0 else 0.0

    # Win Rate & PF
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    total_trades = len(trades)
    win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else 0.0

    gross_profit = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in losses))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 1.0)

    # Sharpe & Sortino Ratio (Daily)
    daily_returns = eq_series.pct_change().dropna()
    mean_ret = float(daily_returns.mean()) if len(daily_returns) > 0 else 0.0
    std_ret = float(daily_returns.std()) if len(daily_returns) > 0 else 1.0
    sharpe = (mean_ret / std_ret * np.sqrt(252)) if std_ret > 0 else 0.0

    downside = daily_returns[daily_returns < 0]
    std_down = float(downside.std()) if len(downside) > 0 else 1.0
    sortino = (mean_ret / std_down * np.sqrt(252)) if std_down > 0 else 0.0

    avg_hold = float(np.mean([t['hold_days'] for t in trades])) if trades else 0.0

    return {
        "days": days_back,
        "trading_days": trading_days,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "strategy_return": round(strategy_return, 2),
        "spy_return": round(spy_return, 2),
        "qqq_return": round(qqq_return, 2),
        "alpha_spy": round(alpha_spy, 2),
        "alpha_qqq": round(alpha_qqq, 2),
        "win_rate": round(win_rate, 1),
        "profit_factor": round(profit_factor, 2),
        "mdd": round(mdd, 2),
        "sharpe": round(sharpe, 2),
        "sortino": round(sortino, 2),
        "total_trades": total_trades,
        "avg_hold_days": round(avg_hold, 1),
        "final_equity": round(final_equity, 2)
    }

def run_all_timeframes():
    """Runs backtest across all 5 timeframes and outputs a consolidated report."""
    data_dict = fetch_historical_dataset(BACKTEST_UNIVERSE, max_days=1150)
    
    results = []
    print("\n" + "="*85)
    print("🚀 [MULTI-TIMEFRAME QUANT STRATEGY BACKTEST VS SPY & QQQ]")
    print("="*85)

    for tf in TIMEFRAMES:
        res = run_simulation(data_dict, tf["days"])
        if res:
            res["timeframe_name"] = tf["name"]
            res["label"] = tf["label"]
            results.append(res)

    print("\n" + "-"*85)
    print(f"{'시간대 (구간)':<14} | {'전략 수익률':<10} | {'SPY 수익률':<10} | {'QQQ 수익률':<10} | {'알파(vs SPY)':<11} | {'승률':<7} | {'PF':<5} | {'MDD':<6} | {'샤프':<5}")
    print("-"*85)
    for r in results:
        sign = "+" if r['strategy_return'] >= 0 else ""
        s_sign = "+" if r['spy_return'] >= 0 else ""
        q_sign = "+" if r['qqq_return'] >= 0 else ""
        a_sign = "+" if r['alpha_spy'] >= 0 else ""
        print(f"{r['timeframe_name']:<14} | {sign}{r['strategy_return']:>7.2f}% | {s_sign}{r['spy_return']:>7.2f}% | {q_sign}{r['qqq_return']:>7.2f}% | {a_sign}{r['alpha_spy']:>8.2f}%p | {r['win_rate']:>5.1f}% | {r['profit_factor']:>4.2f} | -{r['mdd']:>4.1f}% | {r['sharpe']:>4.2f}")
    print("-"*85)

    return results

if __name__ == "__main__":
    run_all_timeframes()
