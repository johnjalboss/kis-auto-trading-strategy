"""전체 매매 시스템 완전 감사"""
import sys, os
os.chdir('/home/ubuntu/kis-auto-trading')
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
import sqlite3
from datetime import datetime, timedelta

print("=" * 65)
print("전체 매매 시스템 완전 감사 보고서")
print("=" * 65)

# ── 1. 실제 성과 분석 ─────────────────────────────────────────────
print("\n[1] 실제 성과 (전체 기간)")
conn = sqlite3.connect('trades.db')
conn.row_factory = sqlite3.Row

sells = conn.execute("""
    SELECT symbol, price, pnl, pnl_pct, reason, created_at, entry_time
    FROM trades WHERE side='SELL' ORDER BY created_at
""").fetchall()

wins = [r for r in sells if (r['pnl'] or 0) > 0]
losses = [r for r in sells if (r['pnl'] or 0) <= 0]
total_pnl = sum(r['pnl'] or 0 for r in sells)
gross_profit = sum(r['pnl'] for r in wins if r['pnl'])
gross_loss = abs(sum(r['pnl'] for r in losses if r['pnl']))
pf = gross_profit / gross_loss if gross_loss > 0 else 99
avg_win = gross_profit / len(wins) if wins else 0
avg_loss = gross_loss / len(losses) if losses else 0

print(f"  총 청산: {len(sells)}건  WR: {len(wins)/len(sells):.0%}  PF: {pf:.2f}")
print(f"  총 P&L: ${total_pnl:+.2f}")
print(f"  평균 수익: ${avg_win:+.2f}  평균 손실: ${avg_loss:-.2f}")
print(f"  기대값(EV): ${(len(wins)/len(sells))*avg_win - (len(losses)/len(sells))*avg_loss:+.3f}/trade")

# ── 청산 이유별 분류 ────────────────────────────────────────────────
print("\n[2] 청산 이유별 성과")
from collections import defaultdict
by_reason = defaultdict(list)
for r in sells:
    reason_short = (r['reason'] or 'UNKNOWN').split(':')[0]
    by_reason[reason_short].append(r['pnl'] or 0)

for reason, pnls in sorted(by_reason.items(), key=lambda x: -len(x[1])):
    cnt = len(pnls)
    tot = sum(pnls)
    wr = sum(1 for p in pnls if p > 0) / cnt
    print(f"  {reason:25} {cnt:3}건 WR={wr:.0%} tot=${tot:+.2f}")

# ── 보유 시간 분석 ─────────────────────────────────────────────────
print("\n[3] 보유 시간 분석")
hold_times = []
for r in sells:
    if r['entry_time'] and r['created_at']:
        try:
            entry = datetime.fromisoformat(r['entry_time'])
            exit_ = datetime.fromisoformat(r['created_at'])
            hold_times.append((exit_ - entry).total_seconds() / 3600)
        except Exception as err:
            print("⚠️ [full_audit.py] Fallback triggered:", err)

if hold_times:
    print(f"  평균 보유: {sum(hold_times)/len(hold_times):.1f}h")
    print(f"  최단: {min(hold_times):.1f}h  최장: {max(hold_times):.1f}h")
    buckets = {'<2h': 0, '2-6h': 0, '6-24h': 0, '1-3d': 0, '3d+': 0}
    for h in hold_times:
        if h < 2: buckets['<2h'] += 1
        elif h < 6: buckets['2-6h'] += 1
        elif h < 24: buckets['6-24h'] += 1
        elif h < 72: buckets['1-3d'] += 1
        else: buckets['3d+'] += 1
    for k, v in buckets.items():
        print(f"    {k}: {v}건")

conn.close()

# ── Config 파라미터 ─────────────────────────────────────────────────
print("\n[4] 핵심 파라미터")
import config
params = ['STOP_LOSS_PCT', 'TAKE_PROFIT_PCT', 'TRAILING_TRIGGER_PCT',
          'TRAILING_STOP_PCT', 'MAX_POSITIONS', 'MAX_DAILY_TRADES']
for p in params:
    print(f"  {p}: {getattr(config, p, 'N/A')}")

# ── 진입 로직 확인 ─────────────────────────────────────────────────
print("\n[5] 진입 조건 핵심 체크")
import inspect
from strategy import StrategyEngine
src = inspect.getsource(StrategyEngine.check_entry)
# RSI 조건
has_rsi = 'RSI' in src or 'rsi' in src
has_macd = 'MACD' in src or 'macd' in src
has_bb = 'BB' in src or 'bollinger' in src.lower()
has_volume = 'volume' in src.lower() or 'VOLUME' in src
has_trend = 'trend' in src.lower() or 'SMA' in src or 'EMA' in src
print(f"  RSI 사용: {has_rsi}  MACD: {has_macd}  BB: {has_bb}")
print(f"  Volume: {has_volume}  Trend: {has_trend}")

# entry 조건 수 확인 (HOLD 반환 횟수 = 차단 조건)
hold_count = src.count('return EntrySignal("HOLD"')
buy_count = src.count('return EntrySignal("BUY"') + src.count('return EntrySignal("STRONG_BUY"')
print(f"  차단 조건: {hold_count}개  진입 조건: {buy_count}개")

# ── 현재 포지션 손익 ────────────────────────────────────────────────
print("\n[6] 현재 포지션 상태")
try:
    from trader import Trader
    t = Trader(config.APP_KEY, config.APP_SECRET, config.ACCOUNT_NO, config.IS_REAL)
    positions = t.get_positions()
    bp = t.get_buying_power()
    total_val = bp
    for p in positions:
        pnl = (p.current_price - p.avg_price) * p.quantity
        pct = (p.current_price / p.avg_price - 1)
        total_val += p.current_price * p.quantity
        print(f"  {p.symbol}: {p.quantity}주 @ ${p.avg_price:.2f} 현재=${p.current_price:.2f} ({pct:+.1%}) ${pnl:+.2f}")
    print(f"  가용현금: ${bp:.2f}  총평가: ${total_val:.2f}")
except Exception as e:
    print(f"  포지션 조회 실패: {e}")

# ── 스크리너 점수 분포 이슈 ──────────────────────────────────────────
print("\n[7] 스크리너 MIN_SCORE 기준 적합성")
from screener import DynamicScreener, ScreenMode
s = DynamicScreener()
print(f"  MIN_SCORE={s.MIN_SCORE}  MAX_RESULTS={s.MAX_RESULTS}")

# ── ATR 손절 vs 고정 손절 비교 ──────────────────────────────────────
print("\n[8] ATR vs 고정손절 분석 (LNTH 예시)")
try:
    from kis_data import get_daily_ohlcv
    import pandas as pd
    df = get_daily_ohlcv('LNTH', days=20)
    if df is not None and len(df) >= 14:
        tr = pd.concat([df['High']-df['Low'],
                        (df['High']-df['Close'].shift()).abs(),
                        (df['Low']-df['Close'].shift()).abs()], axis=1).max(axis=1)
        atr = float(tr.rolling(14).mean().iloc[-1])
        price = float(df['Close'].iloc[-1])
        print(f"  LNTH: price=${price:.2f} ATR=${atr:.2f} ({atr/price:.1%})")
        print(f"  고정손절(-2.5%): ${price*0.975:.2f}  ATR손절(1.5×ATR): ${price-atr*1.5:.2f}")
        print(f"  → 고정 {price*0.025:.2f} vs ATR {atr*1.5:.2f} ({'ATR이 더 넓음' if atr*1.5 > price*0.025 else '고정이 더 넓음'})")
except Exception as e:
    print(f"  ATR 분석 실패: {e}")

print("\n[9] 스윙 트레이딩 핵심 문제 진단")
# EOD 잔재 확인
import subprocess
r = subprocess.run(['grep', '-n', 'EOD\|SWING\|swing\|hold.*day\|MIN_HOLD', 'strategy.py'],
                   capture_output=True, text=True)
for line in r.stdout.strip().split('\n')[:15]:
    print(f"  {line}")
