import sqlite3
import pandas as pd
import glob
import os

with open("avgo_report.txt", "w", encoding="utf-8") as out:
    out.write("=== DB TRADES ===\n")
    for db in ['trades.db', 'trade_journal.db']:
        if os.path.exists(db):
            try:
                conn = sqlite3.connect(db)
                cur = conn.cursor()
                cur.execute("PRAGMA table_info(trades)")
                cols = [c[1] for c in cur.fetchall()]
                target = next((c for c in ['timestamp', 'executed_at', 'date', 'time'] if c in cols), None)
                if target and 'symbol' in cols:
                    df = pd.read_sql_query(f"SELECT * FROM trades WHERE symbol='AVGO' ORDER BY {target} DESC LIMIT 10", conn)
                    out.write(f"--- {db} ---\n{df.to_string()}\n")
                conn.close()
            except Exception as e:
                out.write(f"Error {db}: {e}\n")
                
    out.write("\n=== TEXT LOGS ===\n")
    log_files = ['logs/trading_bot.log', 'remote_trading_bot_latest.log', 'latest_raw_logs.txt', 'bot_log_decoded.txt']
    log_files.extend(glob.glob("*.log"))
    
    for lf in set(log_files):
        if not os.path.exists(lf): continue
        try:
            with open(lf, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()[-30000:]
                # Just keep recent lines with AVGO
                avgo_lines = [l.strip() for l in lines if 'AVGO' in l and ('2026-03-09' in l or '2026-03-10' in l or '2026-03-11' in l)]
                if avgo_lines:
                    out.write(f"\n--- {lf} ---\n")
                    for l in avgo_lines[-50:]: 
                        out.write(l + "\n")
        except Exception as err:
            print("⚠️ [check_avgo.py] Fallback triggered:", err)
