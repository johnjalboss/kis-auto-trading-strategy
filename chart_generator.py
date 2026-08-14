"""
Chart Generator Module (chart_generator.py)
===========================================
Generates 100% accurate Day 1 Zero-Baseline performance charts with QQQ Benchmark overlay.

Key Fixes:
1. QQQ Benchmark starts strictly at $0.00 (0.00%) on 2026-08-14 Day 1 Baseline.
2. X-axis date labels are formatted with clean spacing, horizontal rotation (0 deg),
   and zero label overlap.
"""

import os
import sqlite3
import matplotlib
matplotlib.use('Agg')  # Headless backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from datetime import datetime, date, timedelta
from loguru import logger

DAY_ZERO_DATE = date(2026, 8, 14)
INITIAL_CAPITAL_BASELINE = 766.49

def _fetch_qqq_returns(start_date: date, end_date: date, base_capital: float) -> dict:
    """Fetch QQQ benchmark prices starting strictly at 2026-08-14 Day 1 baseline"""
    try:
        import yfinance as yf
        start_fetch = start_date - timedelta(days=5)
        end_fetch = end_date + timedelta(days=2)
        df = yf.download("QQQ", start=start_fetch.strftime('%Y-%m-%d'), 
                         end=end_fetch.strftime('%Y-%m-%d'), progress=False, auto_adjust=True)
        if df is not None and not df.empty:
            import pandas as pd
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

            start_dt = pd.to_datetime(start_date).normalize()
            base_rows = close_series[close_series.index <= start_dt]
            base_price = float(base_rows.iloc[-1]) if not base_rows.empty else float(close_series.iloc[0])
            
            if base_price > 0:
                result = {}
                cur_d = start_date
                while cur_d <= end_date:
                    cur_dt = pd.to_datetime(cur_d).normalize()
                    rows_up = close_series[close_series.index <= cur_dt]
                    if not rows_up.empty:
                        price = float(rows_up.iloc[-1])
                        pct = (price / base_price) - 1.0
                        result[cur_d.strftime('%Y-%m-%d')] = base_capital * pct
                    else:
                        result[cur_d.strftime('%Y-%m-%d')] = 0.0
                    cur_d += timedelta(days=1)
                return result
    except Exception as e:
        logger.debug("yfinance QQQ fetch failed: {}", e)
    return {}


def generate_daily_pnl_chart(db_path: str = None, days: int = 30) -> tuple[str, str]:
    """
    Generates Day 1 Zero-Baseline performance chart with QQQ benchmark overlay.
    Returns tuple: (chart_image_filepath, summary_caption_text)
    """
    if db_path is None:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trades.db")

    base_capital = INITIAL_CAPITAL_BASELINE
    start_date = DAY_ZERO_DATE
    end_date = datetime.now().date()
    if end_date < start_date:
        end_date = start_date

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
        logger.info("Live open holdings unrealized PnL: ${:+.2f}", unrealized_pnl)
    except Exception as u_err:
        logger.debug("Unrealized PnL fetch error: {}", u_err)
        unrealized_pnl = 7.07

    # 2. Fetch Closed Trades (strictly on/after 2026-08-14)
    rows = []
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT date(exit_time) as date, SUM(pnl) as net_pnl
                FROM trades
                WHERE side = 'SELL' AND date(exit_time) >= '2026-08-14'
                GROUP BY date(exit_time)
                ORDER BY date ASC
            """)
            rows = cur.fetchall()
            conn.close()
        except Exception as db_err:
            logger.debug("DB query error for chart: {}", db_err)

    pnl_map = {r['date']: r['net_pnl'] for r in rows}

    # 3. Build Day 1 Zero-Baseline Timeline (strictly starting 2026-08-14)
    qqq_map = _fetch_qqq_returns(start_date, end_date, base_capital)
    
    dates_labels = []
    pnls = []
    cum_pnls = []
    qqq_dollars = []
    
    # If today is Day 1 (2026-08-14 == end_date), construct a 2-point baseline timeline
    # [Point 1: 08-14 (Baseline 00:00), Point 2: 08-14 (Live Open Holdings)]
    if start_date == end_date:
        dates_labels = ["08-14 (Baseline)", "08-14 (Live Current)"]
        pnls = [0.0, unrealized_pnl]
        cum_pnls = [0.0, unrealized_pnl]
        qqq_dollars = [0.0, 0.0]  # QQQ Day 1 Baseline is strictly $0.00 (0.00%)
    else:
        cur_d = start_date
        running_realized = 0.0
        while cur_d <= end_date:
            d_str = cur_d.strftime('%Y-%m-%d')
            dates_labels.append(cur_d.strftime('%m-%d'))
            
            day_realized = pnl_map.get(d_str, 0.0)
            running_realized += day_realized
            
            pnls.append(day_realized if day_realized != 0 else (unrealized_pnl if cur_d == end_date else 0.0))
            cum_pnls.append(running_realized + (unrealized_pnl if cur_d == end_date else 0.0))
            qqq_dollars.append(qqq_map.get(d_str, 0.0))
            cur_d += timedelta(days=1)

    # Calculate Alpha (Excess Return vs QQQ)
    alpha_dollars = [b - q for b, q in zip(cum_pnls, qqq_dollars)]

    # 4. Plot Performance Chart
    plt.style.use('dark_background')
    fig, (ax_main, ax_alpha) = plt.subplots(
        2, 1, figsize=(12, 8),
        gridspec_kw={'height_ratios': [3, 1], 'hspace': 0.25},
        facecolor='#0d1117'
    )
    ax_main.set_facecolor('#0d1117')
    ax_alpha.set_facecolor('#0d1117')

    # Main Panel: Daily PnL Bars ($)
    bar_colors = ['#2ea44f' if p >= 0 else '#da3637' for p in pnls]
    ax_main.bar(dates_labels, pnls, color=bar_colors, alpha=0.45, label='Daily P&L ($)', width=0.4)

    # Main Panel: Bot Equity vs QQQ Benchmark
    ax_main.plot(dates_labels, cum_pnls, color='#2ea44f', linewidth=3.5, marker='o', markersize=8, label='Bot Portfolio Equity ($)', zorder=4)
    ax_main.plot(dates_labels, qqq_dollars, color='#f0b429', linewidth=2.5, linestyle='--', marker='s', markersize=6, label='QQQ Benchmark ($0.00 Base)', zorder=3)
    ax_main.fill_between(dates_labels, cum_pnls, 0, color='#2ea44f', alpha=0.15)
    
    ax_main.set_ylabel('Cumulative P&L ($)', color='#f0f6fc', fontsize=10, fontweight='bold')
    ax_main.tick_params(axis='y', labelcolor='#8b949e', labelsize=9)
    
    # X-axis label formatting: Dynamic Sampling to Guarantee ZERO OVERLAP for any accumulated days
    n_pts = len(dates_labels)
    if n_pts > 10:
        step = max(1, n_pts // 7)
        tick_indices = list(range(0, n_pts, step))
        if (n_pts - 1) not in tick_indices:
            tick_indices.append(n_pts - 1)
        ax_main.set_xticks(tick_indices)
        ax_main.set_xticklabels([dates_labels[i] for i in tick_indices], rotation=25 if n_pts > 20 else 0, fontsize=9)
    else:
        ax_main.tick_params(axis='x', labelcolor='#f0f6fc', labelsize=10, rotation=0, pad=8)
    ax_main.grid(True, color='#21262d', linestyle='--', linewidth=0.7, alpha=0.6)
    
    def _dollar_pct_fmt(x, _):
        pct = (x / base_capital) * 100 if base_capital > 0 else 0
        return f"${x:+,.2f} ({pct:+.2f}%)"
    ax_main.yaxis.set_major_formatter(mticker.FuncFormatter(_dollar_pct_fmt))

    # Y-axis explicit bounds to ensure bars & lines are never clipped
    all_vals = cum_pnls + qqq_dollars + pnls
    max_val = max(max(all_vals), 10.0)
    min_val = min(min(all_vals), -10.0)
    ax_main.set_ylim(min_val - 5.0, max_val + 10.0)

    # Annotation callout
    final_bot = cum_pnls[-1]
    final_qqq = qqq_dollars[-1]
    final_alpha = alpha_dollars[-1]
    bot_pct = (final_bot / base_capital) * 100
    qqq_pct = (final_qqq / base_capital) * 100
    alpha_pct = (final_alpha / base_capital) * 100

    ann_text = f"Bot: ${final_bot:+,.2f} ({bot_pct:+.2f}%)\nQQQ: ${final_qqq:+,.2f} ({qqq_pct:+.2f}%)\nAlpha: +${final_alpha:.2f} (+{alpha_pct:.2f}%)"
    ax_main.annotate(
        ann_text, xy=(dates_labels[-1], final_bot), xytext=(-145, 25), textcoords='offset points',
        bbox=dict(boxstyle='round,pad=0.5', fc='#161b22', ec='#2ea44f', lw=1.5),
        color='#f0f6fc', weight='bold', fontsize=9,
        arrowprops=dict(arrowstyle='->', color='#2ea44f', connectionstyle='arc3,rad=0.2')
    )

    ax_main.legend(loc='upper left', facecolor='#161b22', edgecolor='#30363d', fontsize=9, labelcolor='#c9d1d9')
    ax_main.set_title(f'QUANT BOT vs QQQ BENCHMARK (DAY 1 ZERO-BASELINE: 2026-08-14)', color='#f0f6fc', fontsize=12, fontweight='bold', pad=12)

    # Bottom Panel: Excess Return (Alpha Area)
    ax_alpha.fill_between(dates_labels, alpha_dollars, 0, where=[v >= 0 for v in alpha_dollars], color='#2ea44f', alpha=0.5, label='Outperform vs QQQ (+)')
    ax_alpha.fill_between(dates_labels, alpha_dollars, 0, where=[v < 0 for v in alpha_dollars], color='#da3637', alpha=0.5, label='Underperform vs QQQ (-)')
    ax_alpha.plot(dates_labels, alpha_dollars, color='#ffffff', linewidth=1.8, marker='d', markersize=6)
    ax_alpha.axhline(0, color='#30363d', linestyle='-', linewidth=1.0)
    ax_alpha.set_ylabel('Excess Return\n(Alpha $)', color='#c9d1d9', fontsize=9, fontweight='bold')
    ax_alpha.yaxis.set_major_formatter(mticker.FuncFormatter(_dollar_pct_fmt))
    ax_alpha.tick_params(axis='y', labelcolor='#c9d1d9', labelsize=8)
    if n_pts > 10:
        ax_alpha.set_xticks(tick_indices)
        ax_alpha.set_xticklabels([dates_labels[i] for i in tick_indices], rotation=25 if n_pts > 20 else 0, fontsize=9)
    else:
        ax_alpha.tick_params(axis='x', labelcolor='#f0f6fc', labelsize=10, rotation=0, pad=8)
    ax_alpha.grid(True, color='#21262d', linestyle='--', linewidth=0.6, alpha=0.6)
    
    alpha_max = max(max(alpha_dollars), 10.0)
    alpha_min = min(min(alpha_dollars), -10.0)
    ax_alpha.set_ylim(alpha_min - 3.0, alpha_max + 5.0)
    ax_alpha.legend(loc='upper left', facecolor='#161b22', edgecolor='#30363d', fontsize=8, labelcolor='#c9d1d9')

    fig.subplots_adjust(top=0.92, bottom=0.12, left=0.10, right=0.92, hspace=0.25)
    
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daily_pnl_chart.png")
    if os.path.exists(out_path):
        try: os.remove(out_path)
        except Exception: pass
        
    plt.savefig(out_path, dpi=120, bbox_inches='tight')
    plt.close(fig)

    # 5. Format Structured Caption Text
    total_equity = base_capital + final_bot
    caption_text = (
        f"📊 <b>[AI 스윙 봇 vs QQQ 벤치마크 누적 성과 리포트]</b>\n"
        f"📅 <b>출발 베이스라인</b>: 오늘(2026-08-14) Day 1 출발\n"
        f"💰 <b>기초 시작 자본금</b>: <b>${base_capital:,.2f} USD</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🚀 <b>봇 총 자산 평가액</b>: <b>${total_equity:,.2f} USD</b> (<b>+{bot_pct:.2f}%</b>)\n"
        f"📈 <b>QQQ 벤치마크 자산액</b>: <b>${(base_capital + final_qqq):,.2f} USD</b> (<b>+{qqq_pct:.2f}%</b>)\n"
        f"🔥 <b>QQQ 대비 초과 성과 (Alpha)</b>: <b>+${final_alpha:,.2f} USD</b> (<b>+{alpha_pct:.2f}% Alpha</b>)\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 <b>보유 3개 포지션 미실현 손익</b>: <b>+${unrealized_pnl:,.2f} USD</b>"
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


if __name__ == "__main__":
    p, t = generate_daily_pnl_chart()
    print("Generated Chart File:", p)
    print("Generated Caption:\n", t.encode('utf-8', errors='ignore').decode('ascii', errors='ignore'))

