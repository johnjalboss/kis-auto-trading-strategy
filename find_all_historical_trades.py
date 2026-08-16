import os, sqlite3, json, glob

print("==========================================================")
print("[SEARCH] SEARCHING FOR ALL HISTORICAL TRADES IN FILES & LOGS")
print("==========================================================")

# 1. Check portfolio_trades.json / portfolio_history.json
for json_file in ["portfolio_trades.json", "portfolio_history.json", "trade_log.json", "position_cache.json"]:
    if os.path.exists(json_file):
        try:
            data = json.load(open(json_file, encoding="utf-8"))
            print(f"File {json_file}: {len(data) if isinstance(data, list) else len(data.keys())} records")
            if isinstance(data, list) and data:
                print("   Sample:", data[:2])
        except Exception as e:
            print(f"File {json_file}: error {e}")

# 2. Check trade_journal.db
if os.path.exists("trade_journal.db"):
    try:
        conn = sqlite3.connect("trade_journal.db")
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print("\ntrade_journal.db Tables:", tables)
        for t in tables:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            cnt = cur.fetchone()[0]
            print(f"   Table '{t}': {cnt} rows")
            if cnt > 0:
                cur.execute(f"SELECT * FROM {t} LIMIT 5")
                print("   Sample:", cur.fetchall())
        conn.close()
    except Exception as e:
        print("trade_journal.db error:", e)

# 3. Check logs directory for SELL executions
log_sells = []
for log_f in glob.glob("logs/*.log"):
    try:
        lines = open(log_f, encoding="utf-8", errors="ignore").readlines()
        for l in lines:
            if "SELL" in l or "매도" in l or "pnl" in l.lower():
                log_sells.append(l.strip())
    except Exception:
        pass

print(f"\nLog files SELL entries found: {len(log_sells)}")
for s in log_sells[:10]:
    print("   Log line:", s)

print("==========================================================")
