import sqlite3, os

def run_deep_audit():
    os.chdir('/home/ubuntu/kis-auto-trading')
    db = sqlite3.connect('trades.db')
    db.row_factory = sqlite3.Row

    print("=== [1] 종료 사유별 손익 분석 ===")
    rows = db.execute("""
        SELECT reason, COUNT(*) as cnt,
               ROUND(AVG(pnl),2) as avg_pnl,
               ROUND(SUM(pnl),2) as total_pnl,
               SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins
        FROM trades WHERE reason IS NOT NULL AND pnl != 0 AND side='SELL'
        GROUP BY reason ORDER BY cnt DESC LIMIT 25
    """).fetchall()
    for r in rows:
        wr = r['wins']/r['cnt']*100 if r['cnt'] > 0 else 0
        print(f"  [{r['cnt']:3d}건|WR:{wr:.0f}%|avg:{r['avg_pnl']:+.2f}|tot:{r['total_pnl']:+.1f}] {str(r['reason'])[:70]}")

    print()
    print("=== [2] 시간대별 성과 (KST 기준 → ET는 -13h) ===")
    rows2 = db.execute("""
        SELECT strftime('%H', exit_time) as h, COUNT(*) as cnt,
               ROUND(AVG(pnl),2) as avg_pnl,
               SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins
        FROM trades WHERE exit_time IS NOT NULL AND pnl != 0 AND side='SELL'
        GROUP BY h ORDER BY h
    """).fetchall()
    for r in rows2:
        wr = r['wins']/r['cnt']*100 if r['cnt'] > 0 else 0
        bar = '█' * int(wr/10)
        print(f"  KST {r['h']}시 | {r['cnt']:3d}건 | WR:{wr:.0f}% {bar} | avg:{r['avg_pnl']:+.2f}")

    print()
    print("=== [3] 종목별 누적 손익 (최악순) ===")
    rows3 = db.execute("""
        SELECT symbol, COUNT(*) as cnt,
               ROUND(SUM(pnl),2) as total_pnl,
               ROUND(AVG(pnl),2) as avg_pnl,
               SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins
        FROM trades WHERE pnl != 0 AND side='SELL'
        GROUP BY symbol ORDER BY total_pnl ASC LIMIT 15
    """).fetchall()
    for r in rows3:
        wr = r['wins']/r['cnt']*100 if r['cnt'] > 0 else 0
        print(f"  {r['symbol']:8s} | {r['cnt']:3d}건 | WR:{wr:.0f}% | avg:{r['avg_pnl']:+.2f} | tot:{r['total_pnl']:+.1f}")

    print()
    print("=== [4] 레짐별 손익 ===")
    rows4 = db.execute("""
        SELECT regime, COUNT(*) as cnt,
               ROUND(AVG(pnl),2) as avg_pnl,
               SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins
        FROM trades WHERE pnl != 0 AND side='SELL' AND regime IS NOT NULL
        GROUP BY regime ORDER BY avg_pnl DESC
    """).fetchall()
    for r in rows4:
        wr = r['wins']/r['cnt']*100 if r['cnt'] > 0 else 0
        print(f"  {r['regime']:20s} | {r['cnt']:3d}건 | WR:{wr:.0f}% | avg:{r['avg_pnl']:+.2f}")

    print()
    print("=== [5] 전체 요약 ===")
    summary = db.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
               SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
               ROUND(SUM(pnl),2) as total_pnl,
               ROUND(AVG(CASE WHEN pnl > 0 THEN pnl END),2) as avg_win,
               ROUND(AVG(CASE WHEN pnl < 0 THEN pnl END),2) as avg_loss,
               ROUND(MAX(pnl),2) as best,
               ROUND(MIN(pnl),2) as worst
        FROM trades WHERE pnl != 0 AND side='SELL'
    """).fetchone()
    if summary['total'] > 0:
        wr = summary['wins']/summary['total']*100
        print(f"  총 {summary['total']}건 | 승률 {wr:.1f}%")
        print(f"  총 P&L: ${summary['total_pnl']:+.2f}")
        print(f"  평균 익절: ${summary['avg_win']:+.2f} | 평균 손절: ${summary['avg_loss']:+.2f}")
        if summary['avg_loss'] and summary['avg_win']:
            rr = abs(summary['avg_win']/summary['avg_loss'])
            ev = (wr/100 * summary['avg_win']) + ((1-wr/100) * summary['avg_loss'])
            print(f"  실제 손익비: {rr:.2f}:1 | 기대값(EV): ${ev:+.2f}/트레이드")
        print(f"  최고 거래: ${summary['best']:+.2f} | 최악 거래: ${summary['worst']:+.2f}")

    db.close()

if __name__ == "__main__":
    run_deep_audit()
