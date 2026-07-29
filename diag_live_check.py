"""
Live data health check — runs on remote server
Checks: FRED cache, Finnhub cache, bot log errors, service crash pattern
"""
import sys, os, json, time, glob
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())
load_dotenv()

now = time.time()
SEP = "=" * 62

print(SEP)
print("LIVE DATA HEALTH CHECK")
print(SEP)

# ── 1. FRED Cache ──────────────────────────────────────────────
print("\n[1] FRED Cache (fred_cache.json)")
try:
    with open("fred_cache.json") as f:
        fc = json.load(f)
    SERIES_IDS = ["T10Y2Y","T10Y3M","FEDFUNDS","DFII10",
                  "BAMLH0A0HYM2","UMCSENT","STLFSI4","SAHMREALTIME","VIXCLS"]
    HIST_IDS   = ["T10Y2Y","M2SL","BAMLH0A0HYM2","WALCL","T10Y3M","FEDFUNDS"]
    ok, miss = [], []
    for sid in SERIES_IDS:
        if sid in fc:
            age_h = (now - fc[sid].get("timestamp",0)) / 3600
            val   = fc[sid].get("value","?")
            ok.append(f"  OK  {sid:22s} val={val!s:10s} age={age_h:.1f}h")
        else:
            miss.append(f"  MISS {sid}")
    for sid in HIST_IDS:
        key = f"{sid}_history"
        if key in fc:
            age_h = (now - fc[key].get("timestamp",0)) / 3600
            n     = len(fc[key].get("data",[]))
            ok.append(f"  OK  {key:26s} rows={n:<6d} age={age_h:.1f}h")
        else:
            miss.append(f"  MISS {key}")
    for line in ok:   print(line)
    for line in miss: print(f"  !! MISSING: {line.strip()}")
    if not miss:
        print("  -> All FRED entries present in cache")
    else:
        print(f"  -> {len(miss)} entries missing from cache (will trigger live API call)")
except FileNotFoundError:
    print("  !! fred_cache.json not found — all FRED data will go live")
except Exception as e:
    print(f"  !! Error reading FRED cache: {e}")

# ── 2. Finnhub Cache ───────────────────────────────────────────
print("\n[2] Finnhub Cache (finnhub_cache.json)")
try:
    sz = os.path.getsize("finnhub_cache.json") / 1024
    with open("finnhub_cache.json") as f:
        fh = json.load(f)
    entries = len(fh)
    old = sum(1 for v in fh.values()
              if isinstance(v, dict) and now - v.get("ts", now) > 86400)
    print(f"  Size : {sz:.0f} KB | Entries: {entries} | Stale(>24h): {old}")
    # check key ticker entries
    KEY_SYMBOLS = ["BINANCE:BTCUSDT","AAPL","NVDA","USO","SPY"]
    for sym in KEY_SYMBOLS:
        if sym in fh:
            v = fh[sym]
            age_h = (now - v.get("ts", now)) / 3600 if isinstance(v, dict) else 999
            print(f"  OK  {sym:20s} age={age_h:.1f}h")
        else:
            print(f"  --  {sym:20s} not cached (will fetch on demand)")
except Exception as e:
    print(f"  !! Finnhub cache error: {e}")

# ── 3. Bot log — last 100 lines for errors ─────────────────────
print("\n[3] Bot Log Errors (last 100 lines)")
log_files = sorted(glob.glob("*.log") + ["current_bot.log","trading_bot.log","bot.log"],
                   key=lambda x: os.path.getmtime(x) if os.path.exists(x) else 0,
                   reverse=True)
found_log = None
for lf in log_files:
    if os.path.exists(lf) and os.path.getsize(lf) > 0:
        found_log = lf
        break

if found_log:
    print(f"  Reading: {found_log}")
    try:
        with open(found_log, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        last100 = lines[-100:]
        errors  = [l.rstrip() for l in last100 if any(
            kw in l for kw in ["ERROR","CRITICAL","Traceback","Exception","failed","FAIL","WARN"]
        )]
        if errors:
            for e in errors[-20:]:   # show last 20 error lines
                print(f"  {e[:120]}")
        else:
            print("  No errors in last 100 lines — clean!")
    except Exception as e:
        print(f"  !! Could not read log: {e}")
else:
    print("  !! No log file found")

# ── 4. FRED live probe ─────────────────────────────────────────
print("\n[4] FRED Live API Probe (direct fetch, no cache)")
fred_key = os.getenv("FRED_API_KEY","")
if fred_key:
    import requests
    probe_ids = ["T10Y2Y","FEDFUNDS","BAMLH0A0HYM2","SAHMREALTIME"]
    for sid in probe_ids:
        try:
            r = requests.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params={"series_id": sid, "api_key": fred_key,
                        "file_type":"json","limit":1,"sort_order":"desc"},
                timeout=8
            )
            obs = r.json().get("observations",[])
            val = obs[0].get("value","?") if obs else "no data"
            print(f"  OK  {sid:20s} = {val}")
        except Exception as e:
            print(f"  !! {sid:20s} FAIL: {e}")
else:
    print("  !! FRED_API_KEY not set — skipping live probe")

print(f"\n{SEP}")
print("DONE")
print(SEP)
