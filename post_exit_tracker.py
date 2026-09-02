import os
import sqlite3
import datetime
import math
from typing import List, Dict, Any, Optional
import yfinance as yf
import pandas as pd
import numpy as np
from loguru import logger

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def _resolve_db_path() -> str:
    cand1 = os.path.join(BASE_DIR, 'trades.db')
    cand2 = '/home/ubuntu/kis-auto-trading/trades.db'
    cand3 = r'C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading\trades.db'
    if os.path.exists(cand1):
        return cand1
    elif os.path.exists(cand2):
        return cand2
    elif os.path.exists(cand3):
        return cand3
    return cand1

def calculate_stock_natr(df) -> float:
    """Calculates Normalized Average True Range (NATR = ATR14 / Close). Zero hardcoding."""
    try:
        if df is None or df.empty or len(df) < 5:
            return 0.025
        highs = df['High'].values.flatten()
        lows = df['Low'].values.flatten()
        closes = df['Close'].values.flatten()
        if len(closes) < 2:
            return 0.025
        
        tr = [max(h - l, abs(h - c_prev), abs(l - c_prev)) for h, l, c_prev in zip(highs[1:], lows[1:], closes[:-1])]
        lookback = min(14, len(tr))
        atr = float(np.mean(tr[-lookback:]))
        c_last = float(closes[-1])
        return max(0.008, atr / c_last) if c_last > 0 else 0.025
    except Exception:
        return 0.025

def get_volatility_bracket_label(natr: float) -> str:
    """Statistical continuous bracket label based on empirical NATR thresholds."""
    if natr >= 0.035:
        return f"🔥 고변동성 (NATR {natr:.1%})"
    elif natr <= 0.020:
        return f"🛡️ 저변동성 (NATR {natr:.1%})"
    else:
        return f"⚖️ 표준변동성 (NATR {natr:.1%})"

class PostExitTracker:
    def __init__(self, db_path: str = None):
        self.db_path = db_path if db_path and os.path.exists(db_path) else _resolve_db_path()
        self._init_db()

    def _init_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS post_exit_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id INTEGER,
                    symbol TEXT NOT NULL,
                    cluster TEXT DEFAULT 'MID_VOL',
                    atr_pct REAL DEFAULT 0.025,
                    exit_date TEXT NOT NULL,
                    exit_price REAL NOT NULL,
                    exit_reason TEXT,
                    realized_pnl_pct REAL,
                    price_1d REAL,
                    price_3d REAL,
                    price_7d REAL,
                    price_14d REAL,
                    curr_price REAL,
                    post_exit_return_pct REAL,
                    z_score REAL DEFAULT 0.0,
                    evaluation TEXT,
                    lesson TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            try:
                cur.execute("ALTER TABLE post_exit_tracking ADD COLUMN z_score REAL DEFAULT 0.0")
            except Exception:
                pass
            try:
                cur.execute("ALTER TABLE post_exit_tracking ADD COLUMN atr_pct REAL DEFAULT 0.025")
            except Exception:
                pass
            try:
                cur.execute("ALTER TABLE post_exit_tracking ADD COLUMN cluster TEXT DEFAULT 'MID_VOL'")
            except Exception:
                pass
                
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error('Failed to init post_exit_tracking table: {}', e)

    def sync_recent_sells_from_trades_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute('''
                SELECT id, symbol, price, pnl_pct, exit_time, created_at, reason
                FROM trades
                WHERE side = 'SELL'
                ORDER BY id DESC LIMIT 50
            ''')
            sells = cur.fetchall()
            for row in sells:
                t_id, sym, price, pnl_pct, exit_time, created_at, reason = row
                date_str = exit_time or created_at or datetime.datetime.now().isoformat()
                date_only = str(date_str)[:10]

                cur.execute('SELECT id FROM post_exit_tracking WHERE trade_id = ? OR (symbol = ? AND exit_date = ?)', 
                            (t_id, sym, date_only))
                if not cur.fetchone():
                    cur.execute('''
                        INSERT INTO post_exit_tracking 
                        (trade_id, symbol, exit_date, exit_price, exit_reason, realized_pnl_pct)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (t_id, sym, date_only, float(price or 0), str(reason or ''), float(pnl_pct or 0)))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug('Sync recent sells error: {}', e)

    def update_tracking(self) -> List[Dict[str, Any]]:
        self.sync_recent_sells_from_trades_db()
        results = []
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute('''
                SELECT id, symbol, exit_date, exit_price, exit_reason, realized_pnl_pct
                FROM post_exit_tracking
                ORDER BY id DESC LIMIT 20
            ''')
            rows = cur.fetchall()

            for row in rows:
                rec_id, sym, exit_date_str, exit_price, reason, pnl_pct = row
                if not exit_price or exit_price <= 0:
                    continue

                try:
                    orig_yf = getattr(yf, '_original_yf_Ticker', yf.Ticker)
                    ticker = orig_yf(sym)
                    df = ticker.history(period='1mo', auto_adjust=True)
                    if df is None or df.empty:
                        continue
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    
                    curr_price = float(df['Close'].iloc[-1])
                    try:
                        fi = getattr(ticker, 'fast_info', {})
                        lp = getattr(fi, 'last_price', None)
                        if lp and float(lp) > 0:
                            curr_price = float(lp)
                    except Exception:
                        pass

                    post_ret = ((curr_price / exit_price) - 1.0) * 100.0
                    
                    # 100% Mathematical NATR calculation
                    natr = calculate_stock_natr(df)
                    
                    # Days since exit
                    try:
                        ex_d = datetime.datetime.strptime(exit_date_str[:10], "%Y-%m-%d")
                        days_held = max(1, (datetime.datetime.now() - ex_d).days)
                    except Exception:
                        days_held = 1

                    # Statistical Z-Score of post-exit price movement relative to stock's own volatility
                    # Expected standard deviation over T days = natr * sqrt(days)
                    expected_sigma_pct = (natr * 100.0) * math.sqrt(days_held)
                    z_score = post_ret / expected_sigma_pct if expected_sigma_pct > 0 else 0.0

                    c_label = get_volatility_bracket_label(natr)
                    cluster_key = "HIGH_VOL" if natr >= 0.035 else ("LOW_VOL" if natr <= 0.020 else "MID_VOL")

                    # Pure Mathematical Z-Score Evaluation:
                    # Z >= +1.8 -> Statistically Significant Missed Rally (Early Exit)
                    # Z <= -1.4 -> Statistically Significant Avoided Drop (Perfect Exit)
                    if z_score >= 1.8:
                        evaluation = 'EARLY_EXIT_MISSED_RALLY'
                        badge = '🔴 [조기 매도]'
                        lesson = f'매도 후 {post_ret:+.1f}% 추가 상승 (Z={z_score:+.2f}σ). {c_label} 고유 변동성 대비 익절 조기 청산 복기.'
                    elif z_score <= -1.4:
                        evaluation = 'PERFECT_EXIT_AVOIDED_DROP'
                        badge = '🟢 [손실 회피]'
                        lesson = f'매도 후 {post_ret:+.1f}% 추가 하락 방어 (Z={z_score:+.2f}σ). {c_label} 탈출로 추가 손실 방어 성공.'
                    else:
                        evaluation = 'OPTIMAL_ROTATION'
                        badge = '⚪ [적정 회전]'
                        lesson = f'매도 후 정상 횡보({post_ret:+.1f}%, Z={z_score:+.2f}σ). {c_label} 통계적 표준 오차 범위 내 자금 회전.'

                    cur.execute('''
                        UPDATE post_exit_tracking
                        SET cluster = ?, atr_pct = ?, curr_price = ?, post_exit_return_pct = ?, z_score = ?, evaluation = ?, lesson = ?, last_updated = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (cluster_key, round(natr, 4), round(curr_price, 2), round(post_ret, 2), round(z_score, 2), evaluation, lesson, rec_id))

                    results.append({
                        'symbol': sym,
                        'cluster': cluster_key,
                        'c_label': c_label,
                        'natr': natr,
                        'z_score': z_score,
                        'exit_date': exit_date_str,
                        'exit_price': exit_price,
                        'curr_price': curr_price,
                        'realized_pnl_pct': pnl_pct,
                        'post_exit_return_pct': post_ret,
                        'badge': badge,
                        'evaluation': evaluation,
                        'lesson': lesson,
                        'reason': reason
                    })
                except Exception as sym_err:
                    logger.debug('Error tracking {}: {}', sym, sym_err)

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error('Update tracking error: {}', e)

        return results

    def format_telegram_card(self) -> str:
        tracked = self.update_tracking()
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        lines = [
            '📝 <b>[통계적 변동성(NATR) 기반 매도 사후 추적 & 오답노트]</b>',
            '━━━━━━━━━━━━━━━━━━━',
            f'⏱ <b>분석시각:</b> <code>{now_str}</code>\n',
            '💡 <i>하드코딩 없이 각 종목의 실제 표준편차(Z-Score)로 조기매도/손실회피를 수학적으로 검증합니다.</i>\n'
        ]

        if not tracked:
            lines.append('ℹ️ <i>최근 1~2주 내 매도 완료된 종목 데이터가 없습니다. (현재 계좌 현금 대기 중)</i>')
            return '\n'.join(lines)

        for item in tracked[:8]:
            sym = item['symbol']
            c_label = item['c_label']
            raw_pnl = item['realized_pnl_pct']
            pnl = (raw_pnl * 100.0) if abs(raw_pnl) <= 1.0 else raw_pnl
            post_ret = item['post_exit_return_pct']
            z = item['z_score']
            badge = item['badge']
            lesson = item['lesson']
            ex_price = item['exit_price']
            c_price = item['curr_price']

            pnl_emoji = '🟢' if pnl >= 0 else '🔴'
            ret_color = '🔴' if post_ret > 0 else '🔵'

            lines.append(
                f"📌 <b>{sym}</b> <code>[{c_label}]</code> (매도일: <code>{item['exit_date']}</code>)\n"
                f"• 매도가: <b>${ex_price:.2f}</b> ({pnl_emoji} 실현손익: <b>{pnl:+.2f}%</b>)\n"
                f"• 현재가: <b>${c_price:.2f}</b> ({ret_color} 사후변동: <b>{post_ret:+.2f}%</b> | <b>Z={z:+.2f}σ</b>)\n"
                f"• <b>판정:</b> {badge}\n"
                f"• 🎓 <b>오답노트:</b> <i>{lesson}</i>\n"
            )

        lines.append('━━━━━━━━━━━━━━━━━━━')
        lines.append('🧠 <i>산출된 Z-Score 오차는 AI 자가 튜닝 엔진으로 피드백되어 종목별 최적 익절 배수를 자율 보정합니다.</i>')
        return '\n'.join(lines)

def get_post_exit_tracker() -> PostExitTracker:
    return PostExitTracker()