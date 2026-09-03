import os, sqlite3, glob

print("==========================================================")
print("🔍 INSPECTING ALL DB TABLES & LOG FILES ON VPS")
print("==========================================================")

# 1. trades.db
if os.path.exists("trades.db"):
    conn = sqlite3.connect("trades.db")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM trades")
    print("trades.db -> trades row count:", cur.fetchone()[0])
    cur.execute("SELECT id, symbol, side, quantity, price, entry_time, exit_time, pnl FROM trades LIMIT 30")
    for r in cur.fetchall():
        print("  ", r)
    conn.close()

# 2. Check for any backup .db files or log files
print("\nScanning for backup db files:")
for db_f in glob.glob("*.db*") + glob.glob("data/*.db*") + glob.glob("backup*/*.db*"):
    print("  DB file found:", db_f, os.path.getsize(db_f), "bytes")

print("==========================================================")
