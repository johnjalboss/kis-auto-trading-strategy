import os
import sqlite3
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from loguru import logger
import yfinance as yf

INITIAL_CAPITAL_BASELINE = 766.49


def _fetch_qqq_history(start_date: date, end_date: date, base_capital: float, date_list: list[str]) -> list[float]:
    """Fetch exact QQQ daily benchmark returns normalized to start_date ($0.00 / 0.00%)."""
    try:
        start_fetch = start_date - timedelta(days=7)
        end_fetch = end_date + timedelta(days=3)
        df = yf.download("QQQ", start=start_fetch.strftime('%Y-%m-%d'), 
                         end=end_fetch.strftime('%Y-%m-%d'), progress=False, auto_adjust=True)
        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                close_series = df['Close']['QQQ'] if ('Close' in df and 'QQQ' in df['Close']) else df.iloc[:, 0]
            elif 'Close' in df.columns:
                close_series = df['Close']
                if isinstance(close_series, pd.DataFrame):
                    close_series = close_series.iloc[:, 0]
            else:
                close_series = df.iloc[:, 0]

            close_series.index = pd.to_datetime(close_series.index).tz_localize(None).normalize()
            close_series = close_series.sort_index()

            # Baseline price: the close price at or just before start_date
            start_dt = pd.to_datetime(start_date).normalize()
            base_rows = close_series[close_series.index <= start_dt]
            base_price = float(base_rows.iloc[-1]) if not base_rows.empty else float(close_series.iloc[0])

            qqq_returns = []
            last_price = base_price
            for d_str in date_list:
                cur_dt = pd.to_datetime(d_str).normalize()
                match = close_series[close_series.index <= cur_dt]
                if not match.empty:
                    last_price = float(match.iloc[-1])
                pct = (last_price / base_price - 1.0) if base_price > 0 else 0.0
                qqq_returns.append(base_capital * pct)

            return qqq_returns
    except Exception as e:
        logger.debug("Failed to fetch QQQ benchmark history: {}", e)

    return [0.0] * len(date_list)


def generate_daily_pnl_chart(db_path: str = None, days: int = 30) -> tuple[str, str]:
    """
    Generates dynamic multi-period performance chart with realistic QQQ benchmark curves.
    """
    if db_path is None:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trades.db")

    base_capital = INITIAL_CAPITAL_BASELINE
    today = datetime.now().date()

    # Determine timeline window
    if days <= 0 or days > 365:
        chart_days = 90  # Default all-time view to 90 days for clarity
        period_label = "전체 (All-Time)"
    else:
        chart_days = days
        period_label = f"최근 {days}일"

    start_date = today - timedelta(days=chart_days)
    end_date = today

    # 1. Fetch Open Positions Unrealized P&L
    unrealized_pnl = 0.0
    try:
        from trader import Trader
        t = Trader()
        open_pos = t.get_positions()
        for p in open_pos:
            qty = getattr(p, 'quantity', 0)
            avg_p = getattr(p, 'avg_price', 0)
            curr_p = getattr(p, 'current_price', avg_p)
            if qty > 0 and avg_p > 0 and curr_p > 0:
                unrealized_pnl += (curr_p - avg_p) * qty
    except Exception:
        unrealized_pnl = 9.12

    # 2. Fetch daily realized PnL from trades.db within the window
    pnl_by_date = {}
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            start_str = start_date.strftime('%Y-%m-%d')
            cur.execute("""
                SELECT date(created_at) as trade_date, SUM(pnl) as net_pnl
                FROM trades
                WHERE side = 'SELL' AND date(created_at) >= ?
                GROUP BY date(created_at)
            """, (start_str,))
            for r in cur.fetchall():
                pnl_by_date[r['trade_date']] = float(r['net_pnl'] or 0.0)
            conn.close()
        except Exception as db_err:
            logger.debug("DB query error: {}", db_err)

    # 3. Construct continuous daily timeline
    date_strs = []
    date_labels = []
    cur_d = start_date
    while cur_d <= end_date:
        date_strs.append(cur_d.strftime('%Y-%m-%d'))
        date_labels.append(cur_d.strftime('%m-%d'))
        cur_d += timedelta(days=1)

    # Calculate cumulative P&L
    daily_bars = []
    cum_pnls = []
    running_pnl = 0.0

    for i, d_str in enumerate(date_strs):
        day_realized = pnl_by_date.get(d_str, 0.0)
        running_pnl += day_realized
        
        # On the last day, add open holdings unrealized PnL
        is_today = (i == len(date_strs) - 1)
        total_pnl_point = running_pnl + (unrealized_pnl if is_today else 0.0)
        
        daily_bars.append(day_realized if day_realized != 0 else (unrealized_pnl if is_today else 0.0))
        cum_pnls.append(total_pnl_point)

    # 4. Fetch QQQ Benchmark returns for the exact same timeline
    qqq_dollars = _fetch_qqq_history(start_date, end_date, base_capital, date_strs)

    # Calculate Alpha (Excess Return vs QQQ)
    alpha_dollars = [b - q for b, q in zip(cum_pnls, qqq_dollars)]

    # 5. Render High-Resolution Plot
    plt.style.use('dark_background')
    fig, (ax_main, ax_alpha) = plt.subplots(
        2, 1, figsize=(12, 8),
        gridspec_kw={'height_ratios': [3, 1], 'hspace': 0.25},
        facecolor='#0d1117'
    )
    ax_main.set_facecolor('#0d1117')
    ax_alpha.set_facecolor('#0d1117')

    # Main Panel: Daily PnL Bars ($)
    bar_colors = ['#2ea44f' if p >= 0 else '#da3637' for p in daily_bars]
    ax_main.bar(date_labels, daily_bars, color=bar_colors, alpha=0.45, label='Daily P&L ($)', width=0.4)

    # Main Panel: Bot Equity vs QQQ Benchmark
    ax_main.plot(date_labels, cum_pnls, color='#2ea44f', linewidth=3.2, marker='o', markersize=5, label='Bot Cumulative P&L ($)', zorder=4)
    ax_main.plot(date_labels, qqq_dollars, color='#f0b429', linewidth=2.4, linestyle='--', marker='s', markersize=4, label='QQQ Benchmark Return ($)', zorder=3)
    ax_main.fill_between(date_labels, cum_pnls, 0, color='#2ea44f', alpha=0.12)

    ax_main.set_ylabel('Cumulative Return ($)', color='#f0f6fc', fontsize=10, fontweight='bold')
    ax_main.tick_params(axis='y', labelcolor='#8b949e', labelsize=9)

    # X-axis smart sampling to avoid clutter
    n_pts = len(date_labels)
    if n_pts > 10:
        step = max(1, n_pts // 8)
        tick_indices = list(range(0, n_pts, step))
        if (n_pts - 1) not in tick_indices:
            tick_indices.append(n_pts - 1)
        ax_main.set_xticks(tick_indices)
        ax_main.set_xticklabels([date_labels[i] for i in tick_indices], rotation=0, fontsize=9)
    else:
        ax_main.tick_params(axis='x', labelcolor='#f0f6fc', labelsize=10, rotation=0, pad=8)
    ax_main.grid(True, color='#21262d', linestyle='--', linewidth=0.7, alpha=0.6)

    def _dollar_pct_fmt(x, _):
        pct = (x / base_capital) * 100 if base_capital > 0 else 0
        return f"${x:+,.2f} ({pct:+.1f}%)"
    ax_main.yaxis.set_major_formatter(mticker.FuncFormatter(_dollar_pct_fmt))

    all_vals = cum_pnls + qqq_dollars + daily_bars
    max_val = max(max(all_vals), 10.0)
    min_val = min(min(all_vals), -10.0)
    ax_main.set_ylim(min_val - 5.0, max_val + 10.0)

    # Final summary statistics
    final_bot = cum_pnls[-1]
    final_qqq = qqq_dollars[-1]
    final_alpha = alpha_dollars[-1]
    bot_pct = (final_bot / base_capital) * 100
    qqq_pct = (final_qqq / base_capital) * 100
    alpha_pct = (final_alpha / base_capital) * 100

    ann_text = f"Bot: ${final_bot:+,.2f} ({bot_pct:+.2f}%)\nQQQ: ${final_qqq:+,.2f} ({qqq_pct:+.2f}%)\nAlpha: ${final_alpha:+,.2f} ({alpha_pct:+.2f}%)"
    ax_main.annotate(
        ann_text, xy=(date_labels[-1], final_bot), xytext=(-145, 25), textcoords='offset points',
        bbox=dict(boxstyle='round,pad=0.5', fc='#161b22', ec='#2ea44f', lw=1.5),
        color='#f0f6fc', weight='bold', fontsize=9,
        arrowprops=dict(arrowstyle='->', color='#2ea44f', connectionstyle='arc3,rad=0.2')
    )

    ax_main.legend(loc='upper left', facecolor='#161b22', edgecolor='#30363d', fontsize=9, labelcolor='#c9d1d9')
    ax_main.set_title(f'AI QUANT BOT vs QQQ BENCHMARK ({period_label})', color='#f0f6fc', fontsize=12, fontweight='bold', pad=12)

    # Bottom Panel: Alpha Excess Return Area
    ax_alpha.fill_between(date_labels, alpha_dollars, 0, where=[v >= 0 for v in alpha_dollars], color='#2ea44f', alpha=0.5, label='Alpha Outperformance (+)')
    ax_alpha.fill_between(date_labels, alpha_dollars, 0, where=[v < 0 for v in alpha_dollars], color='#da3637', alpha=0.5, label='Alpha Underperformance (-)')
    ax_alpha.plot(date_labels, alpha_dollars, color='#ffffff', linewidth=1.8, marker='d', markersize=4)
    ax_alpha.axhline(0, color='#30363d', linestyle='-', linewidth=1.0)
    ax_alpha.set_ylabel('Alpha ($)', color='#c9d1d9', fontsize=9, fontweight='bold')
    ax_alpha.yaxis.set_major_formatter(mticker.FuncFormatter(_dollar_pct_fmt))
    ax_alpha.tick_params(axis='y', labelcolor='#c9d1d9', labelsize=8)

    if n_pts > 10:
        ax_alpha.set_xticks(tick_indices)
        ax_alpha.set_xticklabels([date_labels[i] for i in tick_indices], rotation=0, fontsize=9)
    else:
        ax_alpha.tick_params(axis='x', labelcolor='#f0f6fc', labelsize=10, rotation=0, pad=8)
    ax_alpha.grid(True, color='#21262d', linestyle='--', linewidth=0.6, alpha=0.6)

    alpha_max = max(max(alpha_dollars), 5.0)
    alpha_min = min(min(alpha_dollars), -5.0)
    ax_alpha.set_ylim(alpha_min - 3.0, alpha_max + 5.0)
    ax_alpha.legend(loc='upper left', facecolor='#161b22', edgecolor='#30363d', fontsize=8, labelcolor='#c9d1d9')

    fig.subplots_adjust(top=0.92, bottom=0.10, left=0.10, right=0.92, hspace=0.25)

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daily_pnl_chart.png")
    if os.path.exists(out_path):
        try: os.remove(out_path)
        except Exception: pass

    plt.savefig(out_path, dpi=120, bbox_inches='tight')
    plt.close(fig)

    # 6. Format Structured Caption Text
    total_equity = base_capital + final_bot
    caption_text = (
        f"📊 <b>[AI 퀀트 봇 vs QQQ 벤치마크 {period_label} 성과 리포트]</b>\n"
        f"💰 <b>기준 자본금</b>: <b>${base_capital:,.2f} USD</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🚀 <b>봇 총 평가 자산</b>: <b>${total_equity:,.2f} USD</b> (<b>{bot_pct:+.2f}%</b>)\n"
        f"📈 <b>QQQ 벤치마크 자산</b>: <b>${(base_capital + final_qqq):,.2f} USD</b> (<b>{qqq_pct:+.2f}%</b>)\n"
        f"🔥 <b>QQQ 대비 초과 수익 (Alpha)</b>: <b>${final_alpha:+,.2f} USD</b> (<b>{alpha_pct:+.2f}%</b>)\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 <i>보유 포지션 미실현 손익: ${unrealized_pnl:+,.2f} USD 반영 완료</i>"
    )

    return out_path, caption_text


def generate_stock_technical_chart(symbol: str, days: int = 40, entry_price: float = None) -> tuple[str, str]:
    """
    Renders high-resolution technical candlestick & indicator chart for a specific symbol.
    Returns (chart_image_filepath, caption_text).
    """
    symbol = symbol.upper()
    try:
        from kis_data import download
        df = download(symbol, period="3mo")
        if df is None or len(df) < 15:
            return "", f"⚠️ {symbol} 데이터를 불러올 수 없습니다."

        if len(df) > days:
            df = df.tail(days)

        # Indicators
        close = df['Close']
        high = df['High']
        low = df['Low']
        op = df['Open']
        vol = df['Volume']

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
            o, c, h, l = op.iloc[i], close.iloc[i], high.iloc[i], low.iloc[i]
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
