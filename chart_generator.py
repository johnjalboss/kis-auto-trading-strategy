"""
Chart Generator Module
=======================
Generates performance charts for Telegram/Discord notifications.
Includes QQQ benchmark comparison (dollar-based, faircomparison).

Key fix: Show cumulative P&L in DOLLARS (not %, which was misleading
for small accounts relative to initial_capital denominator).
QQQ "dollar equivalent" = what the starting equity would have returned
if fully invested in QQQ from the chart's start date.
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


def _fetch_qqq_dollar_returns(start_date: date, end_date: date, base_capital: float) -> dict:
    """
    QQQ의 기간별 달러 환산 수익을 반환합니다. (yfinance + KIS API 이중 보장)
    base_capital 만큼 start_date에 QQQ를 샀을 때의 일별 평가이익($)
    """
    df = None
    try:
        import yfinance as yf
        start_fetch = start_date - timedelta(days=7)
        end_fetch = end_date + timedelta(days=1)
        df = yf.download("QQQ",
                         start=start_fetch.strftime('%Y-%m-%d'),
                         end=end_fetch.strftime('%Y-%m-%d'),
                         progress=False, auto_adjust=True)
    except Exception as e:
        logger.debug("yfinance QQQ benchmark fetch failed: {}", e)

    # 폴백: KIS API에서 QQQ 일봉 수집
    if df is None or df.empty:
        try:
            import kis_data
            days_needed = (end_date - start_date).days + 15
            df = kis_data.get_daily_ohlcv("QQQ", days=days_needed)
        except Exception as k_err:
            logger.debug("KIS API QQQ fallback failed: {}", k_err)

    if df is None or df.empty:
        return {}

    try:
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

        # 기준 가격: start_date 당일 또는 바로 이전 거래일 종가
        start_dt = pd.to_datetime(start_date).normalize()
        base_rows = close_series[close_series.index <= start_dt]
        if base_rows.empty:
            base_rows = close_series  # fallback
        base_price = float(base_rows.iloc[-1])
        if base_price <= 0:
            return {}

        # 각 날짜별로 forward-fill하며 달러 P&L 계산 (1일차 = 0.0% / $0.00 출발, 최종 = +21.9% 반영)
        result = {}
        cur_d = start_date
        while cur_d <= end_date:
            cur_dt = pd.to_datetime(cur_d).normalize()
            rows_up = close_series[close_series.index <= cur_dt]
            if not rows_up.empty:
                price = float(rows_up.iloc[-1])
                pct_return = (price / base_price) - 1.0
                result[cur_d.strftime('%Y-%m-%d')] = base_capital * pct_return
            cur_d += timedelta(days=1)
        return result
    except Exception as e:
        logger.debug("QQQ benchmark calc failed: {}", e)
        return {}


def _get_account_equity() -> float:
    """
    실제 계좌 총자산(현금 + 포지션 평가액)을 조회합니다.
    실패하면 None 반환.
    """
    try:
        from trader import Trader
        t = Trader()
        bp = t.get_buying_power()
        positions = t.get_positions()
        total_pos_val = 0.0
        for p in positions:
            qty = getattr(p, 'quantity', 0)
            curr_price = getattr(p, 'current_price', getattr(p, 'avg_price', 0))
            total_pos_val += qty * curr_price
        return bp + total_pos_val
    except Exception as e:
        logger.debug("Equity fetch failed: {}", e)
        return None


def generate_daily_pnl_chart(db_path: str = None, days: int = 90) -> str:
    """Generates a premium dollar-based performance chart with QQQ benchmark overlay."""
    if db_path is None:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trades.db")

    if not os.path.exists(db_path):
        logger.warning(f"DB not found at {db_path} for chart generation")
        return ""

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT MIN(date(exit_time, '-14 hours')) as min_date, MAX(date(exit_time, '-14 hours')) as max_date FROM trades WHERE side = 'SELL'")
        db_range = cur.fetchone()

        if not db_range or not db_range['min_date']:
            logger.info("No sell trades found in database yet. Generating Standby Equity Baseline chart.")
            db_min_date = datetime.now().date() - timedelta(days=7)
            db_max_date = datetime.now().date()
        else:
            db_min_date = datetime.strptime(db_range['min_date'], '%Y-%m-%d').date()
            db_max_date = datetime.strptime(db_range['max_date'], '%Y-%m-%d').date()

        is_all_time = False
        if days is None or days <= 0:
            start_date = db_min_date
            end_date = db_max_date
            actual_days = (end_date - start_date).days + 1
            is_all_time = True
        else:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days - 1)
            actual_days = days

        cur.execute('''
            SELECT
                date(exit_time, '-14 hours') as date,
                SUM(pnl) as net_pnl
            FROM trades
            WHERE side = 'SELL' AND date(exit_time, '-14 hours') IS NOT NULL
            GROUP BY date(exit_time, '-14 hours')
            ORDER BY date ASC
        ''')
        rows = cur.fetchall()
        conn.close()

        pnl_map = {row['date']: row['net_pnl'] for row in rows}

        dates_raw = []
        pnls = []
        current = start_date
        while current <= end_date:
            d_str = current.strftime('%Y-%m-%d')
            dates_raw.append(d_str)
            pnls.append(pnl_map.get(d_str, 0.0))
            current += timedelta(days=1)

        if actual_days > 60:
            dates = dates_raw[:]
        else:
            dates = [d[5:] for d in dates_raw]  # MM-DD

        # ── 보유 포지션 미실현 손익 (Unrealized P&L) 실시간 합산 ──
        unrealized_pnl = 0.0
        try:
            from trader import get_trader
            t = get_trader()
            open_pos = t.get_positions()
            for p in open_pos:
                qty = getattr(p, 'quantity', 0)
                avg_p = getattr(p, 'avg_price', 0)
                curr_p = getattr(p, 'current_price', avg_p)
                if qty > 0 and avg_p > 0 and curr_p > 0:
                    unrealized_pnl += (curr_p - avg_p) * qty
            logger.info("Chart unrealized P&L calculated: ${:+.2f}", unrealized_pnl)
        except Exception as u_err:
            logger.debug("Unrealized P&L calculation failed: {}", u_err)

        # 누적 달러 P&L (실현 손익 + 현재 미실현 손익)
        cum_pnls = []
        s = 0.0
        for idx, p in enumerate(pnls):
            s += p
            # 오늘(차트 마지막 날짜)에는 오픈 포지션 미실현 손익을 반영하여 총자산 수익 표시
            if idx == len(pnls) - 1:
                cum_pnls.append(s + unrealized_pnl)
            else:
                cum_pnls.append(s)

        # ── 기준 자본금: KIS 증권사 실계좌 실측 입금 원금 ($759.86) ──
        try:
            import config
            base_capital = float(getattr(config, 'INITIAL_CAPITAL', 759.86))
        except Exception:
            base_capital = 759.86

        # ── QQQ 벤치마크 달러 환산 ──────────────────────────────────────────
        qqq_dollar_map = _fetch_qqq_dollar_returns(start_date, end_date, base_capital)
        qqq_dollars = [qqq_dollar_map.get(d, None) for d in dates_raw]

        # None forward-fill
        last_val = 0.0
        qqq_dollars_filled = []
        for v in qqq_dollars:
            if v is None:
                qqq_dollars_filled.append(last_val)
            else:
                last_val = v
                qqq_dollars_filled.append(v)

        # 봇 vs QQQ 초과 성과 (달러)
        alpha_dollars = [b - q for b, q in zip(cum_pnls, qqq_dollars_filled)]
        has_qqq = any(abs(v) > 0.01 for v in qqq_dollars_filled)

        # ── 레이아웃 ──────────────────────────────────────────────────────────
        plt.style.use('dark_background')

        if has_qqq:
            fig, (ax_main, ax_alpha) = plt.subplots(
                2, 1, figsize=(14, 9),
                gridspec_kw={'height_ratios': [3, 1], 'hspace': 0.10},
                facecolor='#0d1117'
            )
            ax_main.set_facecolor('#0d1117')
            ax_alpha.set_facecolor('#0d1117')
        else:
            fig, ax_main = plt.subplots(figsize=(14, 7), facecolor='#0d1117')
            ax_main.set_facecolor('#0d1117')
            ax_alpha = None

        ax1 = ax_main

        # ── 위 패널: 일별 P&L 바 (달러) + 누적 P&L 라인 vs QQQ ──────────────
        bar_colors = ['#2ea44f' if p >= 0 else '#da3637' for p in pnls]
        ax1.bar(dates, pnls, color=bar_colors, alpha=0.35, label='Daily P&L ($)',
                width=0.75 if actual_days < 100 else 0.9)
        ax1.set_ylabel('Daily P&L ($)', color='#8b949e', fontsize=10, fontweight='bold')
        ax1.tick_params(axis='y', labelcolor='#8b949e', labelsize=9)
        ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:+,.0f}"))
        ax1.axhline(0, color='#30363d', linestyle='-', linewidth=1.2, alpha=0.9)
        ax1.grid(True, color='#21262d', linestyle='--', linewidth=0.7, alpha=0.6)

        # X축 날짜
        if actual_days > 30:
            step = max(1, actual_days // 12)
            ax1.set_xticks(dates[::step])
            ax1.set_xticklabels(dates[::step], rotation=30, ha='right',
                                color='#8b949e', fontsize=9)
        else:
            ax1.tick_params(axis='x', rotation=30, labelcolor='#8b949e', labelsize=9)

        # 오른쪽 Y축: 누적 P&L ($)
        ax2 = ax1.twinx()
        marker = 'o' if actual_days <= 31 else None

        ax2.plot(dates, cum_pnls, color='#58a6ff', linewidth=2.8,
                 marker=marker, markersize=4, label='Bot Cumulative P&L ($)', zorder=3)
        ax2.fill_between(dates, cum_pnls, 0, color='#58a6ff', alpha=0.12)

        if has_qqq:
            ax2.plot(dates, qqq_dollars_filled, color='#f0b429', linewidth=2.0,
                     linestyle='--', label='QQQ Benchmark PnL ($)', alpha=0.85, zorder=2)

        ax2.set_ylabel('Cumulative P&L ($)', color='#58a6ff', fontsize=10, fontweight='bold')
        ax2.tick_params(axis='y', labelcolor='#58a6ff', labelsize=9)

        # 달러 + 퍼센트 병기 (오른쪽 Y축)
        def _dollar_pct_fmt(x, _):
            pct = (x / base_capital) * 100 if base_capital > 0 else 0
            return f"${x:+,.0f} ({pct:+.1f}%)"
        ax2.yaxis.set_major_formatter(mticker.FuncFormatter(_dollar_pct_fmt))
        ax2.axhline(0, color='#30363d', linestyle=':', linewidth=0.8, alpha=0.5)

        # 0 기준 양 축 대칭 범위
        max_bar = max(abs(min(pnls) if pnls else 0), abs(max(pnls) if pnls else 0), 1)
        ax1.set_ylim(-max_bar * 1.8, max_bar * 1.8)

        all_line_vals = cum_pnls + (qqq_dollars_filled if has_qqq else [])
        max_line = max(abs(min(all_line_vals) if all_line_vals else 0),
                       abs(max(all_line_vals) if all_line_vals else 0), 1)
        ax2.set_ylim(-max_line * 1.5, max_line * 1.5)

        # 최종 말풍선
        if cum_pnls:
            final_bot = cum_pnls[-1]
            final_qqq = qqq_dollars_filled[-1] if has_qqq else None
            final_alpha = alpha_dollars[-1] if has_qqq else None
            bot_pct = (final_bot / base_capital) * 100

            dot_color = '#2ea44f' if final_bot >= 0 else '#da3637'
            ax2.plot(dates[-1], final_bot, 'o', markersize=9,
                     color=dot_color, markeredgecolor='#ffffff', markeredgewidth=1.5, zorder=5)

            ann_parts = [f"Bot: ${final_bot:+,.2f} ({bot_pct:+.1f}%)"]
            if final_qqq is not None:
                qqq_pct = (final_qqq / base_capital) * 100
                ann_parts.append(f"QQQ: ${final_qqq:+,.2f} ({qqq_pct:+.1f}%)")
            if final_alpha is not None:
                alpha_pct = (final_alpha / base_capital) * 100
                sign = "+" if final_alpha >= 0 else ""
                ann_parts.append(f"Excess: {sign}${final_alpha:.2f} ({sign}{alpha_pct:.1f}%)")

            ax2.annotate(
                "\n".join(ann_parts),
                xy=(dates[-1], final_bot),
                xytext=(-130, 28),
                textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.5', fc='#161b22', ec=dot_color, lw=1.5, alpha=0.95),
                color='#f0f6fc', weight='bold', fontsize=9,
                arrowprops=dict(arrowstyle='->', color=dot_color, connectionstyle='arc3,rad=0.2')
            )

        # 범례 통합
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2,
                   loc='upper left', facecolor='#161b22', edgecolor='#30363d',
                   fontsize=9, labelcolor='#c9d1d9')

        title_period = "ALL TIME" if is_all_time else f"LAST {actual_days} DAYS"
        ax1.set_title(f'PERFORMANCE vs QQQ BENCHMARK ({title_period})',
                      color='#f0f6fc', fontsize=13, fontweight='bold', pad=14)

        for ax in [ax1, ax2]:
            ax.spines['top'].set_visible(False)
            ax.spines['bottom'].set_color('#30363d')
            ax.spines['left'].set_color('#30363d')
            ax.spines['right'].set_color('#30363d')

        # ── 아래 패널: 초과 성과($) 영역 ──────────────────────────────────────
        if ax_alpha is not None and has_qqq:
            ax_alpha.fill_between(dates, alpha_dollars, 0,
                                  where=[v >= 0 for v in alpha_dollars],
                                  color='#2ea44f', alpha=0.60, label='Outperform (+)')
            ax_alpha.fill_between(dates, alpha_dollars, 0,
                                  where=[v < 0 for v in alpha_dollars],
                                  color='#da3637', alpha=0.60, label='Underperform (-)')
            ax_alpha.plot(dates, alpha_dollars, color='#e6e6e6', linewidth=1.2, alpha=0.7)
            ax_alpha.axhline(0, color='#30363d', linestyle='-', linewidth=1.0)

            ax_alpha.set_ylabel('Excess vs QQQ\n($)', color='#c9d1d9', fontsize=9, fontweight='bold')

            def _alpha_fmt(x, _):
                pct = (x / base_capital) * 100 if base_capital > 0 else 0
                return f"${x:+,.0f} ({pct:+.1f}%)"
            ax_alpha.yaxis.set_major_formatter(mticker.FuncFormatter(_alpha_fmt))
            ax_alpha.tick_params(axis='y', labelcolor='#c9d1d9', labelsize=8)
            ax_alpha.grid(True, color='#21262d', linestyle='--', linewidth=0.6, alpha=0.6)

            if actual_days > 30:
                step = max(1, actual_days // 12)
                ax_alpha.set_xticks(dates[::step])
                ax_alpha.set_xticklabels(dates[::step], rotation=30, ha='right',
                                         color='#8b949e', fontsize=8)
            else:
                ax_alpha.tick_params(axis='x', rotation=30, labelcolor='#8b949e', labelsize=8)

            # 최종 초과성과 라벨
            final_alpha = alpha_dollars[-1]
            final_alpha_pct = (final_alpha / base_capital) * 100
            fa_color = '#2ea44f' if final_alpha >= 0 else '#da3637'
            sign = "+" if final_alpha >= 0 else ""
            ax_alpha.annotate(
                f" {sign}${final_alpha:.2f} ({sign}{final_alpha_pct:.1f}%) vs QQQ ",
                xy=(dates[-1], final_alpha),
                xytext=(-10, 14 if final_alpha >= 0 else -20),
                textcoords='offset points',
                fontsize=9, weight='bold', color='#f0f6fc',
                bbox=dict(boxstyle='round,pad=0.35', fc=fa_color, ec='#ffffff', lw=1.0, alpha=0.88),
            )

            ax_alpha.legend(loc='upper left', facecolor='#161b22', edgecolor='#30363d',
                            fontsize=8, labelcolor='#c9d1d9')

            for spine in ax_alpha.spines.values():
                spine.set_color('#30363d')
            ax_alpha.spines['top'].set_visible(False)

        plt.tight_layout()

        if is_all_time:
            filename = "performance_all_chart.png"
        else:
            filename = "daily_pnl_chart.png" if actual_days <= 31 else f"performance_{actual_days}d_chart.png"

        out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        if os.path.exists(out_path):
            try:
                os.remove(out_path)
            except Exception as err:
                logger.warning("⚠️ [chart_generator.py] Fallback triggered: {}", err)

        plt.savefig(out_path, dpi=120, bbox_inches='tight')
        plt.close(fig)

        return out_path

    except Exception as e:
        logger.error(f"Failed to generate PnL chart: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return ""


if __name__ == "__main__":
    out = generate_daily_pnl_chart()
    print(f"Chart generated at {out}")
