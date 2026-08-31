"""
audit_chart_evidence.py
Provides exact mathematical proof and daily ledger for the equity curve and daily bars.
"""

import sqlite3
import pandas as pd
import yfinance as yf
from datetime import datetime, date, timedelta

def analyze_chart_evidence():
    print("=" * 70)
    print("📊 [EXACT MATHEMATICAL LEDGER & EVIDENCE FOR THE DAILY CHART]")
    print("=" * 70)

    # 1. Reconstructed Trades
    conn = sqlite3.connect('trades.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT id, symbol, side, quantity, price, pnl, pnl_pct, date(created_at, '-14 hours') as trade_date, created_at
        FROM (
            SELECT id, symbol, side, quantity, price, pnl, pnl_pct, created_at FROM trade_details WHERE date(created_at) >= '2026-08-14'
            UNION ALL
            SELECT id, symbol, side, quantity, price, pnl, pnl_pct, created_at FROM trades WHERE date(created_at) >= '2026-08-14'
        )
        ORDER BY created_at ASC, id ASC
    """)

    seen = set()
    trades = []
    for r in cur.fetchall():
        t_dict = dict(r)
        key = (t_dict['symbol'], t_dict['side'], int(t_dict['quantity'] or 0), round(float(t_dict['price'] or 0), 2), round(float(t_dict['pnl'] or 0), 2), t_dict['trade_date'])
        if key in seen:
            continue
        seen.add(key)
        trades.append(t_dict)

    conn.close()

    print("\n📝 1. ALL RECONSTRUCTED REAL TRADES SINCE AUG 14 (CHRONOLOGICAL):")
    for t in trades:
        print(f"  • {t['trade_date']} | {t['side']:<4} {t['symbol']:<5} x {t['quantity']:>2}주 @ ${float(t['price']):>6.2f} | 실현손익: ${float(t['pnl']):>+6.2f} ({t['created_at']})")

    # 2. Daily Replay Ledger
    start_date = date(2026, 8, 14)
    end_date = date.today()

    initial_positions = {
        'VTOL': {'symbol': 'VTOL', 'quantity': 6, 'avg_price': 45.9246},
        'STRC': {'symbol': 'STRC', 'quantity': 1, 'avg_price': 95.258},
        'MDT': {'symbol': 'MDT', 'quantity': 2, 'avg_price': 88.7533}
    }

    all_symbols_set = set(initial_positions.keys())
    for t in trades:
        all_symbols_set.add(t['symbol'])

    # Fetch daily close
    all_syms = list(all_symbols_set)
    df_hist = yf.download(all_syms, start=(start_date - timedelta(days=5)).strftime('%Y-%m-%d'),
                          end=(end_date + timedelta(days=2)).strftime('%Y-%m-%d'), progress=False, auto_adjust=True)

    hist_prices = {}
    for sym in all_syms:
        try:
            if isinstance(df_hist.columns, pd.MultiIndex):
                c_s = df_hist['Close'][sym] if ('Close' in df_hist and sym in df_hist['Close']) else None
            elif len(all_syms) == 1 and 'Close' in df_hist.columns:
                c_s = df_hist['Close']
            else:
                c_s = None
            if c_s is not None:
                c_s = c_s.dropna()
                c_s.index = pd.to_datetime(c_s.index).tz_localize(None)
                hist_prices[sym] = c_s
        except Exception:
            pass

    # Replay
    running_positions = {k: v.copy() for k, v in initial_positions.items()}
    cum_realized_pnl = 0.0
    trade_cursor = 0
    prev_total_pnl = 0.0

    print("\n" + "=" * 70)
    print("📅 2. DAY-BY-DAY PORTFOLIO MARK-TO-MARKET LEDGER & BAR REASONING:")
    print("=" * 70)

    cur_d = start_date
    day_idx = 0

    while cur_d <= end_date:
        d_str = cur_d.strftime('%Y-%m-%d')
        d_dt = pd.to_datetime(d_str)

        # Apply trades on or before this date
        trades_on_day = []
        while trade_cursor < len(trades):
            tr = trades[trade_cursor]
            if tr['trade_date'] > d_str:
                break
            
            sym = tr['symbol']
            side = tr['side']
            qty = float(tr['quantity'] or 0)
            px = float(tr['price'] or 0)
            pnl_val = float(tr['pnl'] or 0)

            trades_on_day.append(f"{side} {sym} {qty:.0f}주 (${pnl_val:+.2f})")

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

        # Calculate unrealized PnL
        d_unrealized = 0.0
        pos_details = []
        for sym, p_info in running_positions.items():
            qty = p_info['quantity']
            avg_p = p_info['avg_price']
            price_on_day = avg_p
            if sym in hist_prices:
                series = hist_prices[sym]
                match = series[series.index <= d_dt]
                if not match.empty:
                    price_on_day = float(match.iloc[-1])
            
            u_pnl = (price_on_day - avg_p) * qty
            d_unrealized += u_pnl
            pos_details.append(f"{sym} {qty:.0f}주 (종가 ${price_on_day:.2f}, 미실현 ${u_pnl:+.2f})")

        total_pnl_on_day = cum_realized_pnl + d_unrealized
        daily_delta = total_pnl_on_day - prev_total_pnl if day_idx > 0 else total_pnl_on_day
        prev_total_pnl = total_pnl_on_day

        bar_symbol = "🟢 [+]" if daily_delta >= 0 else "🔴 [-]"
        print(f"\n🗓️ [{d_str}] (Day {day_idx + 1}):")
        print(f"   • 당일 체결 거래 : {', '.join(trades_on_day) if trades_on_day else '없음'}")
        print(f"   • 누적 실현 손익 : ${cum_realized_pnl:+,.2f} USD")
        print(f"   • 보유 종목 시총 : {', '.join(pos_details) if pos_details else '현금 100%'}")
        print(f"   • 당일 미실현 손익: ${d_unrealized:+,.2f} USD")
        print(f"   • 당일 총 누적손익: ${total_pnl_on_day:+,.2f} USD")
        print(f"   • 📊 일일 변동 바 : {bar_symbol} ${daily_delta:+,.2f} USD")

        cur_d += timedelta(days=1)
        day_idx += 1

    print("\n" + "=" * 70)

if __name__ == "__main__":
    analyze_chart_evidence()
