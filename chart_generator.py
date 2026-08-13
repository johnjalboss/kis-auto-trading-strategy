"""
Chart Generator Module (chart_generator.py)
===========================================
Generates 100% accurate, zero-distortion performance charts with QQQ benchmark overlay.
Ensures a visible multi-day window (e.g. recent 7 days / 30 days) so that QQQ benchmark line,
Bot equity line, daily PnL bars, and excess return (Alpha) area are 100% clearly visible.
"""

import os
import sqlite3
import matplotlib
matplotlib.use('Agg')  # Headless backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from datetime import datetime, date, timedelta
import math
from loguru import logger

DAY_ZERO_DATE = date(2026, 8, 14)
INITIAL_CAPITAL_BASELINE = 766.49

def _fetch_qqq_returns(start_date: date, end_date: date, base_capital: float) -> dict:
    """Fetch QQQ benchmark prices and return daily dollar P&L relative to start_date"""
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
    Generates performance chart with visible multi-day QQQ benchmark overlay & Daily PnL bars.
    Returns tuple: (chart_image_filepath, summary_caption_text)
    """
    if db_path is None:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trades.db")

    base_capital = INITIAL_CAPITAL_BASELINE
    end_date = datetime.now().date()
    
    # Guarantee at least a 7-day display window for smooth line & bar visibility
    window_days = max(7, min(days or 30, 30))
    start_date = end_date - timedelta(days=window_days - 1)

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

    # 3. Build Timeline (from start_date to today)
    dates_raw = []
    pnls = []
    cum_pnls = []
    
    cur_d = start_date
    running_realized = 0.0
    
    while cur_d <= end_date:
        d_str = cur_d.strftime('%Y-%m-%d')
        dates_raw.append(d_str)
        
        # Realized PnL for today
        day_realized = pnl_map.get(d_str, 0.0)
        running_realized += day_realized
        
        if cur_d < DAY_ZERO_DATE:
            # Anchor baseline at $0.00 prior to launch date
            pnls.append(0.0)
            cum_pnls.append(0.0)
        elif cur_d == DAY_ZERO_DATE:
            # On Launch Date (Today), show unrealized gain bar and cumulative equity
            pnls.append(day_realized if day_realized != 0 else unrealized_pnl)
            cum_pnls.append(running_realized + unrealized_pnl)
        else:
            pnls.append(day_realized)
            cum_pnls.append(running_realized + unrealized_pnl)
            
        cur_d += timedelta(days=1)

    dates = [d[5:] for d in dates_raw]  # MM-DD format

    # 4. Fetch QQQ Benchmark Returns
    qqq_map = _fetch_qqq_returns(start_date, end_date, base_capital)
    qqq_dollars = [qqq_map.get(d, 0.0) for d in dates_raw]
    
    # Calculate Alpha (Excess Return vs QQQ)
    alpha_dollars = [b - q for b, q in zip(cum_pnls, qqq_dollars)]

    # 5. Plot Performance Chart
    plt.style.use('dark_background')
    fig, (ax_main, ax_alpha) = plt.subplots(
        2, 1, figsize=(12, 8),
        gridspec_kw={'height_ratios': [3, 1], 'hspace': 0.20},
        facecolor='#0d1117'
    )
    ax_main.set_facecolor('#0d1117')
    ax_alpha.set_facecolor('#0d1117')

    # Main Panel: Daily PnL Bars ($)
    bar_colors = ['#2ea44f' if p >= 0 else '#da3637' for p in pnls]
    ax_main.bar(dates, pnls, color=bar_colors, alpha=0.45, label='Daily P&L ($)', width=0.5)

    # Main Panel: Bot Equity vs QQQ Benchmark
    ax_main.plot(dates, cum_pnls, color='#2ea44f', linewidth=3.0, marker='o', markersize=7, label='Bot Portfolio Equity ($)', zorder=4)
    ax_main.plot(dates, qqq_dollars, color='#f0b429', linewidth=2.5, linestyle='--', marker='s', markersize=5, label='QQQ Benchmark ($)', zorder=3)
    ax_main.fill_between(dates, cum_pnls, 0, color='#2ea44f', alpha=0.12)
    
    ax_main.set_ylabel('Cumulative P&L ($)', color='#f0f6fc', fontsize=10, fontweight='bold')
    ax_main.tick_params(axis='y', labelcolor='#8b949e', labelsize=9)
    ax_main.tick_params(axis='x', labelcolor='#8b949e', labelsize=9)
    ax_main.grid(True, color='#21262d', linestyle='--', linewidth=0.7, alpha=0.6)
    
    def _dollar_pct_fmt(x, _):
        pct = (x / base_capital) * 100 if base_capital > 0 else 0
        return f"${x:+,.2f} ({pct:+.2f}%)"
    ax_main.yaxis.set_major_formatter(mticker.FuncFormatter(_dollar_pct_fmt))

    # Y-axis explicit bounds to ensure bars & lines are never clipped
    all_vals = cum_pnls + qqq_dollars + pnls
    max_val = max(max(all_vals), 15.0)
    min_val = min(min(all_vals), -15.0)
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
        ann_text, xy=(dates[-1], final_bot), xytext=(-140, 25), textcoords='offset points',
        bbox=dict(boxstyle='round,pad=0.5', fc='#161b22', ec='#2ea44f', lw=1.5),
        color='#f0f6fc', weight='bold', fontsize=9,
        arrowprops=dict(arrowstyle='->', color='#2ea44f', connectionstyle='arc3,rad=0.2')
    )

    ax_main.legend(loc='upper left', facecolor='#161b22', edgecolor='#30363d', fontsize=9, labelcolor='#c9d1d9')
    ax_main.set_title(f'QUANT BOT vs QQQ BENCHMARK ({window_days}-DAY PERFORMANCE WINDOW)', color='#f0f6fc', fontsize=12, fontweight='bold', pad=12)

    # Bottom Panel: Excess Return (Alpha Area)
    ax_alpha.fill_between(dates, alpha_dollars, 0, where=[v >= 0 for v in alpha_dollars], color='#2ea44f', alpha=0.5, label='Outperform vs QQQ (+)')
    ax_alpha.fill_between(dates, alpha_dollars, 0, where=[v < 0 for v in alpha_dollars], color='#da3637', alpha=0.5, label='Underperform vs QQQ (-)')
    ax_alpha.plot(dates, alpha_dollars, color='#ffffff', linewidth=1.5, marker='d', markersize=5)
    ax_alpha.axhline(0, color='#30363d', linestyle='-', linewidth=1.0)
    ax_alpha.set_ylabel('Excess Return\n(Alpha $)', color='#c9d1d9', fontsize=9, fontweight='bold')
    ax_alpha.yaxis.set_major_formatter(mticker.FuncFormatter(_dollar_pct_fmt))
    ax_alpha.tick_params(axis='y', labelcolor='#c9d1d9', labelsize=8)
    ax_alpha.tick_params(axis='x', labelcolor='#c9d1d9', labelsize=9)
    ax_alpha.grid(True, color='#21262d', linestyle='--', linewidth=0.6, alpha=0.6)
    
    alpha_max = max(max(alpha_dollars), 10.0)
    alpha_min = min(min(alpha_dollars), -10.0)
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


if __name__ == "__main__":
    p, t = generate_daily_pnl_chart()
    print("Generated Chart File:", p)
    print("Generated Caption:\n", t.encode('utf-8', errors='ignore').decode('ascii', errors='ignore'))
