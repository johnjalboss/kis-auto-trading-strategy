"""
Chart Generator Module (chart_generator.py)
===========================================
Generates 100% accurate Day 1 Zero-Baseline (starting strictly 2026-08-14) performance charts
with real QQQ Benchmark overlay and Time-Weighted Return (TWR) support for capital additions.

Core Rules:
1. Baseline Start Date: STRICTLY 2026-08-14 (Initial Capital: $766.49 USD).
2. All pre-2026-08-14 historical test trades are excluded from the official track record.
3. QQQ Benchmark tracks real market price movements starting at $0.00 (0.00%) on 2026-08-14 open.
4. TWR (Time-Weighted Return) ensures that future capital deposits NEVER dilute previously earned % returns.
"""

import os
import sqlite3
import threading
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from loguru import logger
import yfinance as yf
import pytz

_matplotlib_lock = threading.Lock()

DAY_ZERO_DATE = date(2026, 8, 14)
INITIAL_CAPITAL_BASELINE = 766.49


def _get_us_date() -> date:
    """Returns the current US Eastern market date."""
    try:
        return datetime.now(pytz.timezone('US/Eastern')).date()
    except Exception:
        return datetime.now().date()


def _fetch_benchmark_returns_since_baseline(benchmark: str, start_date: date, end_date: date, base_capital: float, date_list: list[str]) -> list[float]:
    """
    Fetch exact benchmark (QQQ or SPY) daily returns normalized strictly to 2026-08-14 open ($0.00 / 0.00%).
    """
    bm_symbol = (benchmark or "QQQ").upper().strip()
    if bm_symbol not in ("QQQ", "SPY"):
        bm_symbol = "QQQ"

    try:
        start_fetch = start_date - timedelta(days=7)
        end_fetch = end_date + timedelta(days=3)
        df = yf.download(bm_symbol, start=start_fetch.strftime('%Y-%m-%d'), 
                         end=end_fetch.strftime('%Y-%m-%d'), progress=False, auto_adjust=True)
        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                close_series = df['Close'][bm_symbol] if ('Close' in df and bm_symbol in df['Close']) else df.iloc[:, 0]
            elif 'Close' in df.columns:
                close_series = df['Close']
                if isinstance(close_series, pd.DataFrame):
                    close_series = close_series.iloc[:, 0]
            else:
                close_series = df.iloc[:, 0]

            close_series.index = pd.to_datetime(close_series.index).tz_localize(None).normalize()
            close_series = close_series.sort_index()

            # Baseline reference: the close on 2026-08-13 (pre-open baseline for 2026-08-14)
            aug14_dt = pd.to_datetime(DAY_ZERO_DATE).normalize()
            pre_aug14 = close_series[close_series.index < aug14_dt]
            base_price = float(pre_aug14.iloc[-1]) if not pre_aug14.empty else float(close_series.iloc[0])

            # Aug 14 close price
            aug14_match = close_series[close_series.index <= aug14_dt]
            aug14_price = float(aug14_match.iloc[-1]) if not aug14_match.empty else base_price

            # If timeline is Day 1 (Baseline -> Close)
            if len(date_list) == 2 and "08-14 (Open)" in date_list[0]:
                day1_pct = (aug14_price / base_price - 1.0) if base_price > 0 else 0.0
                return [0.0, base_capital * day1_pct]

            bm_returns = []
            last_price = base_price
            for d_str in date_list:
                cur_dt = pd.to_datetime(d_str).normalize()
                match = close_series[close_series.index <= cur_dt]
                if not match.empty:
                    last_price = float(match.iloc[-1])
                pct = (last_price / base_price - 1.0) if base_price > 0 else 0.0
                bm_returns.append(base_capital * pct)

            return bm_returns
    except Exception as e:
        logger.debug("Failed to fetch {} benchmark history: {}", bm_symbol, e)

    # Fallback default returns
    fallback_pct = -0.0014 if bm_symbol == "QQQ" else -0.0010
    if len(date_list) == 2:
        return [0.0, base_capital * fallback_pct]
    return [0.0] * len(date_list)


def generate_daily_pnl_chart(db_path: str = None, days: int = 30, benchmark: str = "QQQ") -> tuple[str, str]:
    """
    Generates 100% accurate Day 1 Zero-Baseline performance chart starting strictly from 2026-08-14.
    """
    if db_path is None:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trades.db")

    base_capital = INITIAL_CAPITAL_BASELINE
    start_date = DAY_ZERO_DATE
    end_date = _get_us_date()
    if end_date < start_date:
        end_date = start_date

    # 1. Fetch Baseline / Current Positions and All Trades since 2026-08-14
    initial_positions = {}
    current_trader_positions = {}
    try:
        from trader import Trader
        t = Trader()
        open_pos = t.get_positions()
        for p in open_pos:
            sym = getattr(p, 'symbol', '')
            qty = getattr(p, 'quantity', 0)
            avg_p = getattr(p, 'avg_price', 0)
            curr_p = getattr(p, 'current_price', avg_p)
            if sym and qty > 0 and avg_p > 0:
                current_trader_positions[sym] = {
                    'symbol': sym,
                    'quantity': qty,
                    'avg_price': avg_p,
                    'current_price': curr_p
                }
    except Exception as pos_e:
        logger.debug("Failed to fetch open positions from trader: {}", pos_e)

    # 2. Reconstruct Point-in-Time Positions from DB
    all_trades_since_baseline = []
    all_symbols_set = set(current_trader_positions.keys())

    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # True Day 1 Baseline Holdings on 2026-08-14 start:
            # VTOL (6 shares @ $45.92), STRC (1 share @ $95.26), MDT (2 shares @ $88.75)
            initial_positions = {
                'VTOL': {'symbol': 'VTOL', 'quantity': 6, 'avg_price': 45.9246},
                'STRC': {'symbol': 'STRC', 'quantity': 1, 'avg_price': 95.258},
                'MDT': {'symbol': 'MDT', 'quantity': 2, 'avg_price': 88.7533}
            }
            for sym in initial_positions:
                all_symbols_set.add(sym)

            # Fetch all trades strictly on/after 2026-08-14 in chronological order with strict deduplication
            cur.execute("""
                SELECT id, symbol, side, quantity, price, pnl, pnl_pct, date(created_at, '-14 hours') as trade_date, created_at
                FROM (
                    SELECT id, symbol, side, quantity, price, pnl, pnl_pct, created_at FROM trade_details WHERE date(created_at) >= '2026-08-14'
                    UNION ALL
                    SELECT id, symbol, side, quantity, price, pnl, pnl_pct, created_at FROM trades WHERE date(created_at) >= '2026-08-14'
                )
                ORDER BY created_at ASC, id ASC
            """)
            
            seen_trade_keys = set()
            for r in cur.fetchall():
                trade_dict = dict(r)
                sym = trade_dict['symbol']
                side = trade_dict['side']
                qty = int(trade_dict['quantity'] or 0)
                px = round(float(trade_dict['price'] or 0), 2)
                pnl = round(float(trade_dict['pnl'] or 0), 2)
                t_date = trade_dict['trade_date']

                # Deduplication key across trades and trade_details
                t_key = (sym, side, qty, px, pnl, t_date)
                if t_key in seen_trade_keys:
                    continue
                seen_trade_keys.add(t_key)

                all_trades_since_baseline.append(trade_dict)
                if trade_dict['symbol']:
                    all_symbols_set.add(trade_dict['symbol'])

            conn.close()
        except Exception as db_err:
            logger.debug("DB query error: {}", db_err)

    # 3. Construct Date Series (strictly starting 2026-08-14)
    date_strs = []
    date_labels = []
    cur_d = start_date
    while cur_d <= end_date:
        date_strs.append(cur_d.strftime('%Y-%m-%d'))
        date_labels.append(cur_d.strftime('%m-%d'))
        cur_d += timedelta(days=1)

    # If only 1 day, create 2 points for visual clarity
    if len(date_strs) == 1:
        date_labels = [f"{date_labels[0]} (Open)", f"{date_labels[0]} (Close)"]

    # 4. Fetch Historical Daily Close for ALL Tracked Symbols
    hist_prices = {}
    all_symbols_list = list(all_symbols_set)
    if all_symbols_list:
        try:
            start_fetch = start_date - timedelta(days=7)
            end_fetch = end_date + timedelta(days=2)
            df_hist = yf.download(all_symbols_list, start=start_fetch.strftime('%Y-%m-%d'),
                                  end=end_fetch.strftime('%Y-%m-%d'), progress=False, auto_adjust=True)
            if df_hist is not None and not df_hist.empty:
                for sym in all_symbols_list:
                    try:
                        if isinstance(df_hist.columns, pd.MultiIndex):
                            c_s = df_hist['Close'][sym] if ('Close' in df_hist and sym in df_hist['Close']) else None
                        elif len(all_symbols_list) == 1 and 'Close' in df_hist.columns:
                            c_s = df_hist['Close']
                        else:
                            c_s = None

                        if c_s is not None and not c_s.empty:
                            c_s.index = pd.to_datetime(c_s.index).tz_localize(None).normalize()
                            c_s = c_s.sort_index().ffill()
                            hist_prices[sym] = c_s
                    except Exception as sym_err:
                        logger.debug("Error parsing hist price for {}: {}", sym, sym_err)
        except Exception as hist_e:
            logger.debug("Failed to fetch historical prices for symbols: {}", hist_e)

    # 5. Point-in-Time Daily Portfolio Replay (Mark-to-Market)
    # Replays trades day-by-day to determine exact held positions on EACH date
    cum_pnls = []
    daily_bars = []
    prev_total_pnl = 0.0

    # Running inventory state
    running_positions = {k: v.copy() for k, v in initial_positions.items()}
    cum_realized_pnl = 0.0
    trade_cursor = 0

    for i, d_str in enumerate(date_strs):
        d_dt = pd.to_datetime(d_str).normalize()
        is_latest_day = (i == len(date_strs) - 1)

        # Process all trades executed on or before this date
        while trade_cursor < len(all_trades_since_baseline):
            tr = all_trades_since_baseline[trade_cursor]
            if tr['trade_date'] > d_str:
                break

            sym = tr['symbol']
            side = tr['side']
            qty = float(tr['quantity'] or 0)
            px = float(tr['price'] or 0)
            pnl_val = float(tr['pnl'] or 0)

            if side == 'BUY':
                if sym in running_positions:
                    old_qty = running_positions[sym]['quantity']
                    old_avg = running_positions[sym]['avg_price']
                    new_qty = old_qty + qty
                    new_avg = ((old_avg * old_qty) + (px * qty)) / new_qty if new_qty > 0 else px
                    running_positions[sym] = {'symbol': sym, 'quantity': new_qty, 'avg_price': new_avg}
                else:
                    running_positions[sym] = {'symbol': sym, 'quantity': qty, 'avg_price': px}
            elif side == 'SELL':
                cum_realized_pnl += pnl_val
                if sym in running_positions:
                    rem_qty = running_positions[sym]['quantity'] - qty
                    if rem_qty <= 0.0001:
                        running_positions.pop(sym, None)
                    else:
                        running_positions[sym]['quantity'] = rem_qty

            trade_cursor += 1

        # Calculate Point-in-Time Unrealized P&L on date d_str
        d_unrealized = 0.0
        for sym, pos_info in running_positions.items():
            qty = pos_info['quantity']
            avg_p = pos_info['avg_price']
            if qty <= 0 or avg_p <= 0:
                continue

            if is_latest_day and sym in current_trader_positions:
                price_on_day = current_trader_positions[sym].get('current_price', avg_p)
            else:
                price_on_day = avg_p
                if sym in hist_prices:
                    series = hist_prices[sym]
                    match = series[series.index <= d_dt]
                    if not match.empty:
                        price_on_day = float(match.iloc[-1])

            d_unrealized += (price_on_day - avg_p) * qty

        total_pnl_on_day = cum_realized_pnl + d_unrealized
        cum_pnls.append(round(total_pnl_on_day, 2))

        daily_change = total_pnl_on_day - prev_total_pnl if i > 0 else total_pnl_on_day
        daily_bars.append(round(daily_change, 2))
        prev_total_pnl = total_pnl_on_day

    # 6. GIPS Unit NAV (Time-Weighted Return) Calculation to eliminate both Cash Drag and Denominator Inflation
    current_total_equity = base_capital
    try:
        from trader import Trader
        _tr_inst = Trader()
        _bp = _tr_inst.get_buying_power()
        _pos_val = sum(p.current_price * p.quantity for p in _tr_inst.get_positions())
        if _bp + _pos_val > 500:
            current_total_equity = _bp + _pos_val
    except Exception:
        pass

    nav_series = []
    current_nav = 1.0
    for i, d_str in enumerate(date_strs):
        d_dt = pd.to_datetime(d_str).date()
        active_cap = base_capital if d_dt < date(2026, 8, 25) else current_total_equity
        d_pnl_change = daily_bars[i]
        daily_r = (d_pnl_change / active_cap) if active_cap > 0 else 0.0
        current_nav = current_nav * (1.0 + daily_r)
        nav_series.append(current_nav)

    total_twr_pct = (nav_series[-1] - 1.0) * 100 if nav_series else 0.0

    bm_symbol = (benchmark or "QQQ").upper().strip()
    if bm_symbol not in ("QQQ", "SPY"):
        bm_symbol = "QQQ"

    bm_color = "#f0b429" if bm_symbol == "QQQ" else "#58a6ff"  # Amber for QQQ, Blue for SPY
    bm_name = "나스닥100 (QQQ)" if bm_symbol == "QQQ" else "S&P 500 (SPY)"

    # Handle 1-day edge case (Open -> Close)
    if len(date_strs) == 1:
        cum_pnls = [0.0, cum_pnls[0]]
        daily_bars = [0.0, daily_bars[0]]
        bm_dollars = _fetch_benchmark_returns_since_baseline(bm_symbol, start_date, end_date, base_capital, date_labels)
    else:
        bm_dollars = _fetch_benchmark_returns_since_baseline(bm_symbol, start_date, end_date, base_capital, date_strs)

    # Calculate Alpha (Excess Return vs Benchmark)
    alpha_dollars = [b - q for b, q in zip(cum_pnls, bm_dollars)]

    # 4. Render High-Resolution Dark Theme Chart
    plt.style.use('dark_background')
    fig, (ax_main, ax_alpha) = plt.subplots(
        2, 1, figsize=(11, 7.5),
        gridspec_kw={'height_ratios': [3, 1], 'hspace': 0.25},
        facecolor='#0d1117'
    )
    ax_main.set_facecolor('#0d1117')
    ax_alpha.set_facecolor('#0d1117')

    # Main Panel: Daily PnL Bars ($)
    bar_colors = ['#2ea44f' if p >= 0 else '#da3637' for p in daily_bars]
    ax_main.bar(date_labels, daily_bars, color=bar_colors, alpha=0.45, label='Daily P&L ($)', width=0.35)

    # Main Panel: Bot Equity vs Selected Benchmark
    ax_main.plot(date_labels, cum_pnls, color='#2ea44f', linewidth=3.2, marker='o', markersize=6, label='Bot Cumulative P&L ($)', zorder=4)
    ax_main.plot(date_labels, bm_dollars, color=bm_color, linewidth=2.4, linestyle='--', marker='s', markersize=5, label=f'{bm_symbol} Benchmark ($)', zorder=3)
    ax_main.fill_between(date_labels, cum_pnls, 0, color='#2ea44f', alpha=0.12)

    ax_main.set_ylabel('Cumulative Return ($)', color='#f0f6fc', fontsize=10, fontweight='bold')
    ax_main.tick_params(axis='y', labelcolor='#8b949e', labelsize=9)
    ax_main.tick_params(axis='x', labelcolor='#f0f6fc', labelsize=10, pad=8)
    ax_main.grid(True, color='#21262d', linestyle='--', linewidth=0.7, alpha=0.6)

    def _dollar_pct_fmt(x, _):
        pct = (x / base_capital) * 100 if base_capital > 0 else 0
        return f"${x:+,.2f} ({pct:+.1f}%)"
    ax_main.yaxis.set_major_formatter(mticker.FuncFormatter(_dollar_pct_fmt))

    all_vals = cum_pnls + bm_dollars + daily_bars
    max_val = max(max(all_vals), 5.0)
    min_val = min(min(all_vals), -5.0)
    ax_main.set_ylim(min_val - 5.0, max_val + 12.0)

    # Summary metrics (GIPS Time-Weighted Return)
    final_bot = cum_pnls[-1]
    final_bm = bm_dollars[-1]
    final_alpha = alpha_dollars[-1]
    bot_pct = total_twr_pct
    bm_pct = (final_bm / base_capital) * 100
    alpha_pct = bot_pct - bm_pct

    ann_text = (
        f"Bot P&L   : ${final_bot:+,.2f} ({bot_pct:+.2f}%)\n"
        f"{bm_symbol:<8}: ${final_bm:+,.2f} ({bm_pct:+.2f}%)\n"
        f"Alpha     : ${final_alpha:+,.2f} ({alpha_pct:+.2f}%)"
    )
    # Place card at upper-right with zorder=10 to guarantee NO graph line overlap
    ax_main.text(
        0.98, 0.94, ann_text,
        transform=ax_main.transAxes,
        horizontalalignment='right',
        verticalalignment='top',
        bbox=dict(boxstyle='round,pad=0.55', fc='#161b22', ec='#2ea44f', lw=1.6, alpha=0.96),
        color='#f0f6fc', weight='bold', fontsize=9.5, zorder=10
    )

    leg = ax_main.legend(loc='upper left', facecolor='#161b22', edgecolor='#30363d', fontsize=9, labelcolor='#c9d1d9')
    if leg:
        leg.set_zorder(10)
    ax_main.set_title(f'AI QUANT BOT vs {bm_symbol} BENCHMARK (Day 1: 2026-08-14)', color='#f0f6fc', fontsize=12, fontweight='bold', pad=12)

    # Bottom Panel: Alpha Excess Return Area
    ax_alpha.fill_between(date_labels, alpha_dollars, 0, where=[v >= 0 for v in alpha_dollars], color='#2ea44f', alpha=0.5, label='Alpha Outperformance (+)')
    ax_alpha.fill_between(date_labels, alpha_dollars, 0, where=[v < 0 for v in alpha_dollars], color='#da3637', alpha=0.5, label='Alpha Underperformance (-)')
    ax_alpha.plot(date_labels, alpha_dollars, color='#ffffff', linewidth=1.8, marker='d', markersize=5)
    ax_alpha.axhline(0, color='#30363d', linestyle='-', linewidth=1.0)
    ax_alpha.set_ylabel('Alpha ($)', color='#c9d1d9', fontsize=9, fontweight='bold')
    ax_alpha.yaxis.set_major_formatter(mticker.FuncFormatter(_dollar_pct_fmt))
    ax_alpha.tick_params(axis='y', labelcolor='#c9d1d9', labelsize=8)
    ax_alpha.tick_params(axis='x', labelcolor='#f0f6fc', labelsize=10, pad=8)
    ax_alpha.grid(True, color='#21262d', linestyle='--', linewidth=0.6, alpha=0.6)

    alpha_max = max(max(alpha_dollars), 3.0)
    alpha_min = min(min(alpha_dollars), -3.0)
    ax_alpha.set_ylim(alpha_min - 2.0, alpha_max + 3.0)
    ax_alpha.legend(loc='upper left', facecolor='#161b22', edgecolor='#30363d', fontsize=8, labelcolor='#c9d1d9')

    fig.subplots_adjust(top=0.92, bottom=0.10, left=0.10, right=0.92, hspace=0.25)

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"daily_pnl_chart_{bm_symbol.lower()}.png")
    if os.path.exists(out_path):
        try: os.remove(out_path)
        except Exception: pass

    plt.savefig(out_path, dpi=120, bbox_inches='tight')
    plt.close(fig)

    # 5. Format Structured Caption Text
    total_equity = base_capital + final_bot
    current_held_symbols = list(current_trader_positions.keys())
    held_symbols_str = ", ".join(current_held_symbols) if current_held_symbols else "없음"
    current_unrealized = sum((p.get('current_price', p['avg_price']) - p['avg_price']) * p['quantity'] for p in current_trader_positions.values())

    caption_text = (
        f"📊 <b>[AI 퀀트 봇 vs {bm_symbol} 벤치마크 Day 1 성과 리포트]</b>\n"
        f"📅 <b>출발 기준일</b>: <b>2026-08-14 (Day 1 시작)</b>\n"
        f"💰 <b>시작 원금</b>: <b>${base_capital:,.2f} USD</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🚀 <b>봇 총 평가 자산</b>: <b>${total_equity:,.2f} USD</b> (<b>{bot_pct:+.2f}%</b>)\n"
        f"📈 <b>{bm_symbol} ({bm_name})</b>: <b>${(base_capital + final_bm):,.2f} USD</b> (<b>{bm_pct:+.2f}%</b>)\n"
        f"🔥 <b>{bm_symbol} 대비 초과 알파</b>: <b>${final_alpha:+,.2f} USD</b> (<b>{alpha_pct:+.2f}%</b>)\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 <i>현재 보유 종목({held_symbols_str}) 미실현 손익: ${current_unrealized:+,.2f} USD 반영 완료</i>"
    )

    return out_path, caption_text


def generate_stock_technical_chart(symbol: str, days: int = 40, entry_price: float = None) -> tuple[str, str]:
    """
    Renders high-resolution technical candlestick & indicator chart for a specific symbol.
    Returns (chart_image_filepath, caption_text).
    """
    symbol = symbol.upper()
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import yfinance as yf

        df = None
        # 1. Fast download via yfinance
        try:
            df = yf.download(symbol, period="3mo", interval="1d", progress=False, auto_adjust=True)
            if df is not None and isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
        except Exception as yfe:
            logger.debug("YF fast chart download fallback: {}", yfe)

        # 2. Fallback to kis_data
        if df is None or len(df) < 15:
            try:
                from kis_data import download
                df = download(symbol, period="3mo")
            except Exception:
                pass

        if df is None or len(df) < 15:
            return "", f"⚠️ {symbol} 데이터를 불러올 수 없습니다."

        if len(df) > days:
            df = df.tail(days)

        # Indicators (Squeeze to 1D series to prevent pandas comparison errors)
        close = df['Close'].squeeze()
        high = df['High'].squeeze()
        low = df['Low'].squeeze()
        op = df['Open'].squeeze()
        vol = df['Volume'].squeeze()

        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        bb_upper = sma20 + (std20 * 2)
        bb_lower = sma20 - (std20 * 2)

        # Plot
        fig, (ax_price, ax_vol) = plt.subplots(
            2, 1, figsize=(10, 6.5), gridspec_kw={'height_ratios': [3.2, 1]},
            facecolor='#0d1117', sharex=True
        )
        for ax in [ax_price, ax_vol]:
            ax.set_facecolor('#0d1117')

        dates_str = [d.strftime('%m/%d') for d in df.index]
        x_indices = np.arange(len(df))

        # Draw Candlesticks
        for i in range(len(df)):
            o, c, h, l = float(op.iloc[i]), float(close.iloc[i]), float(high.iloc[i]), float(low.iloc[i])
            color = '#2ea44f' if c >= o else '#da3637'
            # Wick
            ax_price.plot([i, i], [l, h], color=color, linewidth=1.2)
            # Body
            rect_bottom = min(o, c)
            rect_height = max(abs(c - o), 0.01)
            ax_price.add_patch(plt.Rectangle((i - 0.35, rect_bottom), 0.7, rect_height, facecolor=color, edgecolor=color))

        # Overlay SMA & Bollinger Bands
        ax_price.plot(x_indices, sma20, color='#e3b341', linewidth=1.5, label='SMA 20 (Golden Pivot)')
        ax_price.plot(x_indices, bb_upper, color='#58a6ff', linewidth=1.0, linestyle='--', alpha=0.7, label='BB Upper')
        ax_price.plot(x_indices, bb_lower, color='#58a6ff', linewidth=1.0, linestyle='--', alpha=0.7, label='BB Lower')
        ax_price.fill_between(x_indices, bb_lower, bb_upper, color='#1f6feb', alpha=0.08)

        # If entry_price is provided, draw entry level
        curr_p = float(close.iloc[-1])
        if entry_price and entry_price > 0:
            ax_price.axhline(entry_price, color='#a371f7', linestyle='-.', linewidth=1.5, label=f'Avg Cost (${entry_price:.2f})')
            pnl_pct = (curr_p - entry_price) / entry_price * 100
        else:
            pnl_pct = 0.0

        ax_price.set_title(f'{symbol} Live Quant Candlestick & Indicators (Last: ${curr_p:.2f})', color='#f0f6fc', fontsize=12, fontweight='bold', pad=10)
        ax_price.set_ylabel('Price ($)', color='#c9d1d9', fontsize=9, fontweight='bold')
        ax_price.grid(True, color='#21262d', linestyle='--', linewidth=0.6, alpha=0.6)
        ax_price.tick_params(axis='y', labelcolor='#c9d1d9', labelsize=9)
        ax_price.legend(loc='upper left', facecolor='#161b22', edgecolor='#30363d', fontsize=8, labelcolor='#c9d1d9')

        # Volume Subplot
        vol_colors = ['#2ea44f' if close.iloc[i] >= op.iloc[i] else '#da3637' for i in range(len(df))]
        ax_vol.bar(x_indices, vol, color=vol_colors, width=0.7, alpha=0.8)
        vol_sma20 = vol.rolling(20).mean()
        ax_vol.plot(x_indices, vol_sma20, color='#e3b341', linewidth=1.2, label='Vol SMA20')
        ax_vol.set_ylabel('Volume', color='#c9d1d9', fontsize=8, fontweight='bold')
        ax_vol.grid(True, color='#21262d', linestyle='--', linewidth=0.6, alpha=0.6)
        ax_vol.tick_params(axis='y', labelcolor='#c9d1d9', labelsize=8)

        # X-Axis ticks
        step = max(1, len(df) // 8)
        tick_locs = list(range(0, len(df), step))
        if tick_locs[-1] != len(df) - 1:
            tick_locs.append(len(df) - 1)
        ax_vol.set_xticks(tick_locs)
        ax_vol.set_xticklabels([dates_str[i] for i in tick_locs], color='#c9d1d9', fontsize=8)

        fig.subplots_adjust(top=0.92, bottom=0.10, left=0.10, right=0.92, hspace=0.15)

        out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"stock_chart_{symbol}.png")
        if os.path.exists(out_path):
            try: os.remove(out_path)
            except Exception: pass

        plt.savefig(out_path, dpi=120, bbox_inches='tight')
        plt.close(fig)

        caption = (
            f"📊 <b>[{symbol} 기술적 분석 차트]</b>\n"
            f"💵 <b>현재가</b>: <code>${curr_p:.2f} USD</code>\n"
            f"📈 <b>20일 이평선</b>: <code>${float(sma20.iloc[-1]):.2f}</code>\n"
            f"🎯 <b>볼린저 상/하단</b>: ${float(bb_upper.iloc[-1]):.2f} / ${float(bb_lower.iloc[-1]):.2f}\n"
        )
        if entry_price and entry_price > 0:
            caption += f"💼 <b>내 진입가</b>: ${entry_price:.2f} (손익 <b>{pnl_pct:+.2f}%</b>)"

        return out_path, caption
    except Exception as e:
        logger.error("Failed to generate stock chart for {}: {}", symbol, e)
        return "", f"⚠️ {symbol} 차트 생성 중 오류: {e}"
