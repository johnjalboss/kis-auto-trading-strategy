"""
Fetch dashboard data from KIS API on the server.
Run on Oracle server via SSH.
"""
import json
import os
import subprocess
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(BASE_DIR, "position_cache.json")

data = {
    "status": "OFFLINE",
    "positions": [],
    "buying_power": 0,
    "total_value": 0,
    "total_pnl": 0,
    "errors": "0",
    "log": "",
    "exchange_rate": 1400.0,
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

# 1. Bot status
try:
    data["status"] = subprocess.getoutput("sudo systemctl is-active kis-trading").strip()
except Exception as err:
    logger.warning("⚠️ [fetch_dashboard_data.py] Fallback triggered: {}", err)

# 2. Positions from KIS API (read token directly, never request new one)
try:
    import os, sys, re, requests
    from dotenv import load_dotenv
    load_dotenv()
    
    # Suppress loguru output
    from loguru import logger
    logger.remove()
    logger.add(sys.stderr, level="ERROR")
    
    import config
    
    app_key = config.KIS_APP_KEY
    app_secret = config.KIS_APP_SECRET
    account_no = config.KIS_CANO
    account_cd = config.KIS_ACNT_PRDT_CD
    is_paper = config.IS_PAPER_TRADING
    base_url = "https://openapivts.koreainvestment.com:29443" if is_paper else "https://openapi.koreainvestment.com:9443"
    
    # Read existing token from file (DO NOT request new token - it will invalidate bot's token)
    token = None
    token_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.json")
    if os.path.exists(token_file):
        with open(token_file) as f:
            token_data = json.load(f)
        token = token_data.get("access_token")
    
    if not token:
        raise ValueError("No token.json found - bot may not be running")
    
    def _headers(tr_id):
        return {
            "Content-Type": "application/json; charset=UTF-8",
            "authorization": f"Bearer {token}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": tr_id,
        }
    
    # Get positions across all exchanges
    tr_id = "VTTS3012R" if is_paper else "TTTS3012R"
    url = f"{base_url}/uapi/overseas-stock/v1/trading/inquire-balance"
    
    pos_data = []
    bp = 0.0
    api_success = False
    
    import time
    for excd in ["NASD", "NYSE", "AMEX"]:
        params = {
            "CANO": account_no,
            "ACNT_PRDT_CD": account_cd,
            "OVRS_EXCG_CD": excd,
            "TR_CRCY_CD": "USD",
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": ""
        }
        try:
            resp = requests.get(url, headers=_headers(tr_id), params=params, timeout=10)
            api_data = resp.json()
            time.sleep(0.2)  # Rate limit
            
            if api_data.get("rt_cd") == "0":
                api_success = True
                for item in api_data.get("output1", []):
                    qty = int(item.get("ovrs_cblc_qty", 0))
                    if qty > 0:
                        symbol = item.get("ovrs_pdno", "")
                        avg_price = float(item.get("pchs_avg_pric", 0))
                        cur_price = float(item.get("now_pric2", 0))
                        
                        # Live pre/post market price enhancement
                        try:
                            import yfinance as yf
                            tk = yf.Ticker(symbol)
                            live_p = getattr(tk.fast_info, 'last_price', None)
                            if live_p and float(live_p) > 0:
                                cur_price = float(live_p)
                        except Exception:
                            pass

                        if cur_price <= 0:
                            cur_price = avg_price
                        
                        existing = next((p for p in pos_data if p["symbol"] == symbol), None)
                        if existing:
                            continue # Account balance is global, do not sum duplicates
                        else:
                            pnl_pct = ((cur_price - avg_price) / avg_price * 100) if avg_price > 0 else 0
                            pos_data.append({
                                "symbol": symbol,
                                "qty": qty,
                                "entry": round(avg_price, 2),
                                "current": round(cur_price, 2),
                                "pnl_pct": round(pnl_pct, 2),
                                "value": round(cur_price * qty, 2)
                            })

        except Exception as err:
            logger.warning("⚠️ [fetch_dashboard_data.py] Fallback triggered: {}", err)
            
    # 2.2 Precise Buying Power Discovery (using inquire-psamount if bp is still 0 or low)
    if bp <= 0:
        try:
            # Overseas Orderable Amount Inquiry (TTTS3007R)
            ps_tr_id = "VTTS3007R" if is_paper else "TTTS3007R"
            ps_url = f"{base_url}/uapi/overseas-stock/v1/trading/inquire-psamount"
            
            # Need a dummy symbol for this API, use AAPL or any common one
            ps_params = {
                "CANO": account_no,
                "ACNT_PRDT_CD": account_cd,
                "OVRS_EXCG_CD": "NASD",
                "OVRS_ORD_UNPR": "150.00",
                "ITEM_CD": "AAPL"
            }
            
            ps_resp = requests.get(ps_url, headers=_headers(ps_tr_id), params=ps_params, timeout=10)
            ps_data = ps_resp.json()
            
            if ps_data.get("rt_cd") == "0":
                out = ps_data.get("output", {})
                # Prefer integrated amount (frcr_ord_psbl_amt1)
                val1 = out.get("frcr_ord_psbl_amt1", "0")
                val2 = out.get("ovrs_ord_psbl_amt", "0")
                bp = float(val1) if float(val1) > 0 else float(val2)
                # Ensure we capture exchange rate
                exrt = out.get("exrt", "1400")
                if exrt and float(exrt) > 0:
                    data["exchange_rate"] = float(exrt)
        except Exception as err:
            logger.warning("⚠️ [fetch_dashboard_data.py] Fallback triggered: {}", err)
    
    # If API returned positions, save to cache for off-hours use
    if api_success:
        try:
            # Load existing cache to get old bp if current is 0
            if bp <= 0:
                if os.path.exists(CACHE_FILE):
                    with open(CACHE_FILE) as f:
                        old_bp = json.load(f).get("buying_power", 0)
                        if old_bp > 0:
                            bp = old_bp
        except Exception as err:
            logger.warning("⚠️ [fetch_dashboard_data.py] Fallback triggered: {}", err)
    
    # If API returned no data (off-hours), load everything from cache
    if not pos_data and not api_success:
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE) as f:
                    cache = json.load(f)
                pos_data = cache.get("positions", [])
                # Mark as cached data
                for p in pos_data:
                    p["from_cache"] = True
                if bp <= 0:
                    bp = cache.get("buying_power", 0)
        except Exception as err:
            logger.warning("⚠️ [fetch_dashboard_data.py] Fallback triggered: {}", err)
    
    # Buying power fallback from log or cache if API returned 0
    if bp <= 0:
        try:
            # 1. Try cache first
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE) as f:
                    cache = json.load(f)
                bp = cache.get("buying_power", 0)
            
            # 2. Try Log (DEPRECATED: leads to stale $500 reports)
            pass
        except Exception as err:
            logger.warning("⚠️ [fetch_dashboard_data.py] Fallback triggered: {}", err)
    
    # Update cache ONLY if we have valid data (or if we want to update positions)
    # We always save positions, but only overwrite BP if it's > 0
    try:
        current_cache = {}
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE) as f:
                current_cache = json.load(f)
        
        new_bp = bp if bp > 0 else current_cache.get("buying_power", 0)
        
        cache_data = {
            "positions": pos_data if pos_data else current_cache.get("positions", []),
            "buying_power": new_bp,
            "cached_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f)
    except Exception as err:
        logger.warning("⚠️ [fetch_dashboard_data.py] Fallback triggered: {}", err)
    
    data["positions"] = pos_data
    data["buying_power"] = round(bp, 2)
    data["total_value"] = round(bp + sum(p["value"] for p in pos_data), 2)
    data["total_pnl"] = round(sum((p["current"] - p["entry"]) * p["qty"] for p in pos_data), 2)
except Exception as e:
    # Fallback: load from position cache
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE) as f:
                cache = json.load(f)
            data["positions"] = cache.get("positions", [])
            for p in data["positions"]:
                p["from_cache"] = True
            data["buying_power"] = cache.get("buying_power", 0)
            data["total_value"] = data["buying_power"] + sum(p["value"] for p in data["positions"])
            data["total_pnl"] = sum((p["current"] - p["entry"]) * p["qty"] for p in data["positions"])
    except Exception as err:
        logger.warning("⚠️ [fetch_dashboard_data.py] Fallback triggered: {}", err)
    
    # Last resort: buying power from log ONLY if it's still 0
    if data.get("buying_power", 0) <= 0:
        try:
            import re
            log_bp = subprocess.getoutput("grep 'Buying Power' ~/kis-auto-trading/remote_trading_bot.log | tail -1")
            bp_match = re.search(r'Buying Power: \$([0-9,.]+)', log_bp)
            if bp_match:
                data["buying_power"] = float(bp_match.group(1).replace(',', ''))
                if data.get("total_value", 0) <= 0:
                    data["total_value"] = data["buying_power"]
        except Exception as err:
            logger.warning("⚠️ [fetch_dashboard_data.py] Fallback triggered: {}", err)
    data["error_msg"] = str(e)

# 3. Recent log (strip ANSI colors)
try:
    raw_log = subprocess.getoutput("tail -20 ~/kis-auto-trading/logs/trading_bot.log 2>/dev/null")
    import re
    data["log"] = re.sub(r'\x1b\[[0-9;]*m', '', raw_log)
except Exception as err:
    logger.warning("⚠️ [fetch_dashboard_data.py] Fallback triggered: {}", err)

# 4. Error count
try:
    err_out = subprocess.getoutput("grep -c 'FATAL' ~/kis-auto-trading/logs/trading_bot.log 2>/dev/null || echo 0").strip()
    data["errors"] = err_out.split('\n')[0].strip()
except Exception as err:
    logger.warning("⚠️ [fetch_dashboard_data.py] Fallback triggered: {}", err)

# 5. Extract historical PnL from trades.db
try:
    import sqlite3
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "trades.db")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Get overall net pnl and trading days to calculate CAGR strictly since 2026-08-14 Day 1
        try:
            DAY_ZERO_STR = "2026-08-14"
            row = cur.execute("""
                SELECT SUM(pnl) as net_pnl
                FROM (
                    SELECT pnl FROM trade_details WHERE side = 'SELL' AND date(created_at) >= ? AND pnl IS NOT NULL
                    UNION ALL
                    SELECT pnl FROM trades WHERE side = 'SELL' AND date(created_at) >= ? AND pnl IS NOT NULL
                )
            """, (DAY_ZERO_STR, DAY_ZERO_STR)).fetchone()
            
            realized_pnl = float(row["net_pnl"] or 0.0) if row else 0.0
            
            # Days elapsed since Day 1 (at least 1)
            from datetime import date
            day_zero = date(2026, 8, 14)
            today_d = datetime.now().date()
            trading_days = max(1, (today_d - day_zero).days + 1)
            
            # Calculate total net profit (realized since 08-14 + current unrealized)
            open_unrealized = sum((p["current"] - p["entry"]) * p["qty"] for p in data.get("positions", []))
            total_net_profit = realized_pnl + open_unrealized
            
            # Baseline capital: $766.49 USD
            initial_capital = 766.49
            current_total_value = initial_capital + total_net_profit
            
            if initial_capital > 0:
                # Daily CAGR / Arithmetic return
                total_return_pct = (total_net_profit / initial_capital) * 100
                daily_avg_pct = total_return_pct / trading_days
                data["avg_daily_pnl_pct"] = round(daily_avg_pct, 4)
            else:
                data["avg_daily_pnl_pct"] = 0.0
                
        except Exception as e:
            data["avg_daily_pnl_pct"] = 0.0
            data["cagr_error"] = str(e)
            
        # Get daily stats dynamically from trade_details and trades tables
        cur.execute("""
            SELECT 
                date(created_at, '-14 hours') as date, 
                SUM(pnl) as net_pnl, 
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins, 
                SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as losses 
            FROM (
                SELECT pnl, created_at FROM trade_details WHERE side = 'SELL' AND created_at IS NOT NULL
                UNION ALL
                SELECT pnl, COALESCE(exit_time, created_at) as created_at FROM trades WHERE side = 'SELL' AND created_at IS NOT NULL
            )
            WHERE date(created_at, '-14 hours') IS NOT NULL
            GROUP BY date(created_at, '-14 hours')
            ORDER BY date DESC
        """)
        db_history = {row["date"]: {k: row[k] for k in row.keys()} for row in cur.fetchall()}
        
        # Build continuous last 365 days
        from datetime import date, timedelta
        end_date = datetime.now().date()
        history = []
        for i in range(364, -1, -1):
            d_str = (end_date - timedelta(days=i)).strftime("%Y-%m-%d")
            entry = db_history.get(d_str, {
                "date": d_str,
                "net_pnl": 0,
                "wins": 0,
                "losses": 0
            })
            total_trades = entry["wins"] + entry["losses"]
            entry["win_rate"] = entry["wins"] / total_trades if total_trades > 0 else 0
            history.append(entry)
            
        data["history"] = history
        conn.close()
    else:
        data["history"] = []
        data["avg_daily_pnl_pct"] = 0
except Exception as e:
    data["history_error"] = str(e)
    data["history"] = []
    data["avg_daily_pnl_pct"] = 0

print(json.dumps(data))
