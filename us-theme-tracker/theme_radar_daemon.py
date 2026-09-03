import os
import sys
import io
import time
import json
import sqlite3
import datetime
import traceback
import pytz
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
import yfinance as yf
from loguru import logger

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
THEME_DB_JSON = os.path.join(BASE_DIR, "theme_db.json")
DB_PATH = os.path.join(BASE_DIR, "us_stocks_data.db")
STATUS_JSON = os.path.join(BASE_DIR, "theme_radar_status.json")
CACHE_JSON = os.path.join(BASE_DIR, "theme_radar_cache.json")

# Configure UTF-8 logger
logger.remove()
utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
logger.add(
    utf8_stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
    level="INFO"
)
logger.add(
    os.path.join(BASE_DIR, "theme_radar_daemon.log"),
    rotation="10 MB",
    retention="5 days",
    level="INFO",
    encoding="utf-8"
)

def get_volume_scale_factor(last_date_str: str) -> float:
    """미국 동부 시간(US/Eastern) 기준 기관 U-Curve 장중 누적 거래량 곡선 적용"""
    tz = pytz.timezone('US/Eastern')
    now_est = datetime.datetime.now(tz)
    today_est_str = now_est.strftime("%Y-%m-%d")
    
    if last_date_str != today_est_str:
        return 1.0
        
    current_minutes = now_est.hour * 60 + now_est.minute
    open_minutes = 9 * 60 + 30  # 09:30 -> 570
    close_minutes = 16 * 60     # 16:00 -> 960
    
    if current_minutes < open_minutes or current_minutes >= close_minutes:
        return 1.0
        
    elapsed = float(current_minutes - open_minutes)
    
    if elapsed <= 30.0:
        pct_completed = max(0.08, (elapsed / 30.0) * 0.18)
    elif elapsed <= 120.0:
        pct_completed = 0.18 + ((elapsed - 30.0) / 90.0) * 0.22
    elif elapsed <= 270.0:
        pct_completed = 0.40 + ((elapsed - 120.0) / 150.0) * 0.28
    elif elapsed <= 360.0:
        pct_completed = 0.68 + ((elapsed - 270.0) / 90.0) * 0.20
    else:
        pct_completed = 0.88 + ((elapsed - 360.0) / 30.0) * 0.12

    return min(10.0, max(1.0, 1.0 / pct_completed))

def get_market_state() -> str:
    """
    Returns 'REGULAR' (09:30-16:00 EST), 'EXTENDED' (04:00-09:30 or 16:00-20:00 EST), or 'CLOSED'.
    """
    try:
        tz = pytz.timezone('US/Eastern')
        now_est = datetime.datetime.now(tz)
        if now_est.weekday() >= 5:
            return "CLOSED"
            
        current_minutes = now_est.hour * 60 + now_est.minute
        if 9 * 60 + 30 <= current_minutes < 16 * 60:
            return "REGULAR"
        elif 4 * 60 <= current_minutes < 20 * 60:
            return "EXTENDED"
        else:
            return "CLOSED"
    except Exception:
        return "CLOSED"

class ThemeRadarDaemon:
    def __init__(self):
        self.themes_config = {}
        self.theme_tickers = {}
        self.all_unique_tickers = []
        self.raw_daily = pd.DataFrame()
        self.last_daily_fetch = None
        self.prev_signals = {}
        self.prev_true_themes = set()
        self.load_config()

    def load_config(self):
        if not os.path.exists(THEME_DB_JSON):
            logger.error("theme_db.json not found!")
            return
            
        with open(THEME_DB_JSON, "r", encoding="utf-8") as f:
            self.themes_config = json.load(f).get("themes", {})
            
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cur = conn.cursor()
        
        self.theme_tickers = {}
        for tid, cfg in self.themes_config.items():
            pm = cfg.get("premapped_tickers", [])
            cur.execute("SELECT ticker FROM stock_metadata WHERE theme_tags LIKE ?", (f"%{tid}%",))
            db_ticks = [r[0] for r in cur.fetchall()]
            all_ticks = list(dict.fromkeys(pm + db_ticks))[:35]
            if len(all_ticks) >= 2:
                self.theme_tickers[tid] = all_ticks
                
        conn.close()
        
        self.all_unique_tickers = list(dict.fromkeys(
            t for ticks in self.theme_tickers.values() for t in ticks
        ))
        if "SPY" not in self.all_unique_tickers:
            self.all_unique_tickers.append("SPY")
            
        logger.info("Loaded {} active themes with {} unique tickers.",
                    len(self.theme_tickers), len(self.all_unique_tickers))

    def fetch_daily_history(self, force: bool = False):
        """Fetch 6-month daily historical OHLCV data with intelligent hourly refresh"""
        now = time.time()
        if not force and self.last_daily_fetch and (now - self.last_daily_fetch < 1800) and not self.raw_daily.empty:
            return
            
        logger.info("Refreshing daily historical baseline for {} tickers...", len(self.all_unique_tickers))
        chunk_size = 100
        daily_chunks = []
        import gc
        
        for i in range(0, len(self.all_unique_tickers), chunk_size):
            chunk = self.all_unique_tickers[i:i+chunk_size]
            try:
                raw_c = yf.download(
                    chunk, period="6mo", interval="1d", auto_adjust=True,
                    progress=False, threads=True, group_by="ticker"
                )
                if not raw_c.empty:
                    daily_chunks.append(raw_c)
            except Exception as e:
                logger.warning("Error downloading daily chunk {}: {}", i, e)
            time.sleep(0.1)
                
        if daily_chunks:
            self.raw_daily = pd.concat(daily_chunks, axis=1)
            self.last_daily_fetch = now
            del daily_chunks
            gc.collect()
            logger.info("Daily baseline updated successfully.")

    def fetch_live_snapshots(self) -> pd.DataFrame:
        """Lightweight live snapshot fetcher (reuses daily baseline to eliminate CPU/RAM spikes)"""
        return pd.DataFrame()

    def run_cycle(self):
        cycle_start = time.time()
        m_state = get_market_state()
        logger.info("Running Theme Radar Cycle (Market State: {})...", m_state)
        
        # 1. Ensure daily baseline is fresh
        self.fetch_daily_history()
        if self.raw_daily.empty:
            logger.warning("Daily baseline empty, skipping cycle.")
            return
            
        # 2. Fetch live streaming / snapshot prices
        raw_live = self.fetch_live_snapshots()
        
        # Helper for extracting series
        def get_series(df, ticker, col):
            try:
                if isinstance(df.columns, pd.MultiIndex):
                    return df[ticker][col].dropna()
                else:
                    return df[col].dropna() if col in df.columns else pd.Series(dtype=float)
            except Exception:
                return pd.Series(dtype=float)

        # 3. SPY Benchmark Momentum
        spy_c = get_series(self.raw_daily, "SPY", "Close")
        spy_ret20 = float((spy_c.iloc[-1] / spy_c.iloc[-21] - 1) * 100) if len(spy_c) >= 21 else 0.0
        spy_ret60 = float((spy_c.iloc[-1] / spy_c.iloc[-60] - 1) * 100) if len(spy_c) >= 60 else spy_ret20

        # Load previous signals for hysteresis
        try:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            cur = conn.cursor()
            cur.execute("SELECT theme_id, signal_type FROM theme_signals")
            self.prev_signals = {r[0]: r[1] for r in cur.fetchall()}
            conn.close()
        except Exception:
            pass

        results = []
        for tid, ticks in self.theme_tickers.items():
            stock_metrics = []
            for t in ticks:
                c = get_series(self.raw_daily, t, "Close")
                v = get_series(self.raw_daily, t, "Volume")
                if len(c) < 22 or pd.isna(c.iloc[-1]) or pd.isna(c.iloc[-2]):
                    continue

                ret_1d  = float((c.iloc[-1]/c.iloc[-2]-1)*100)  if len(c)>=2  else 0.0
                ret_5d  = float((c.iloc[-1]/c.iloc[-6]-1)*100)  if len(c)>=6  else ret_1d
                ret_20d = float((c.iloc[-1]/c.iloc[-21]-1)*100) if len(c)>=21 else ret_5d
                ret_60d = float((c.iloc[-1]/c.iloc[-60]-1)*100) if len(c)>=60 else ret_20d

                if len(v) >= 21:
                    last_date_str = v.index[-1].strftime("%Y-%m-%d")
                    scale_factor = get_volume_scale_factor(last_date_str)
                    today_v = float(v.iloc[-1]) * scale_factor
                    avg_v   = float(v.iloc[-21:-1].mean())
                    if pd.isna(today_v) or pd.isna(avg_v) or avg_v <= 0:
                        rvol = 1.0
                    else:
                        rvol = min(5.0, max(0.01, today_v / avg_v))
                else:
                    rvol = 1.0

                daily_returns = c.iloc[-21:].pct_change().dropna()
                daily_vol = float(daily_returns.std() * 100) if len(daily_returns) > 0 else 2.0

                ma20 = float(c.iloc[-20:].mean()) if len(c)>=20 else float(c.iloc[-1])
                ma50 = float(c.iloc[-50:].mean()) if len(c)>=50 else float(c.iloc[-1])
                ma200 = float(c.iloc[-200:].mean()) if len(c)>=200 else float(c.iloc[-1])
                above_ma20 = bool(c.iloc[-1] > ma20)
                above_ma50 = bool(c.iloc[-1] > ma50)
                is_ma_aligned = bool(ma20 > ma50 > ma200)

                # Live / pre-market price integration
                live_c = get_series(raw_live, t, "Close")
                live_price = float(live_c.iloc[-1]) if (not raw_live.empty and len(live_c) > 0) else float(c.iloc[-1])

                stock_metrics.append({
                    "ret_1d": ret_1d, "ret_5d": ret_5d, "ret_20d": ret_20d, "ret_60d": ret_60d,
                    "rvol": rvol, "above_ma20": above_ma20, "above_ma50": above_ma50,
                    "is_ma_aligned": is_ma_aligned, "is_up_1d": bool(ret_1d > 0),
                    "price": live_price, "ticker": t, "daily_vol": round(daily_vol, 2),
                })

            n = len(stock_metrics)
            if n == 0:
                continue

            rvol_vals = [s["rvol"] for s in stock_metrics if s["rvol"] is not None and not np.isnan(s["rvol"])]
            ret1d_vals = [s["ret_1d"] for s in stock_metrics if s["ret_1d"] is not None and not np.isnan(s["ret_1d"])]
            ret5d_vals = [s["ret_5d"] for s in stock_metrics if s["ret_5d"] is not None and not np.isnan(s["ret_5d"])]
            ret20d_vals = [s["ret_20d"] for s in stock_metrics if s["ret_20d"] is not None and not np.isnan(s["ret_20d"])]
            ret60d_vals = [s["ret_60d"] for s in stock_metrics if s["ret_60d"] is not None and not np.isnan(s["ret_60d"])]

            med_rvol   = float(np.median(rvol_vals)) if rvol_vals else 1.0
            med_ret1d  = float(np.median(ret1d_vals)) if ret1d_vals else 0.0
            med_ret5d  = float(np.median(ret5d_vals)) if ret5d_vals else 0.0
            med_ret20d = float(np.median(ret20d_vals)) if ret20d_vals else 0.0
            med_ret60d = float(np.median(ret60d_vals)) if ret60d_vals else 0.0

            breadth_1d     = sum(s["is_up_1d"]        for s in stock_metrics) / n * 100
            breadth_5d     = sum(s["ret_5d"] > 0       for s in stock_metrics) / n * 100
            above_ma_pct   = sum(s["above_ma20"]       for s in stock_metrics) / n * 100
            above_ma50_pct = sum(s["above_ma50"]       for s in stock_metrics) / n * 100
            ma_align_pct   = sum(s["is_ma_aligned"]    for s in stock_metrics) / n * 100

            # ── 5-Factor Quantitative Engine ──
            score = 0
            # F1: RVOL (25 pts)
            if med_rvol >= 2.5: f1 = 25
            elif med_rvol >= 1.0: f1 = round(12 + (med_rvol - 1.0) / 1.5 * 13)
            elif med_rvol >= 0.5: f1 = round(4 + (med_rvol - 0.5) / 0.5 * 8)
            else: f1 = round(max(0, med_rvol / 0.5 * 4))
            score += f1

            # F2: Momentum 5D (20 pts)
            if 2.0 <= med_ret5d <= 5.0: f2 = 20
            elif 5.0 < med_ret5d <= 8.0: f2 = round(20 - (med_ret5d - 5.0) / 3.0 * 10)
            elif med_ret5d > 8.0: f2 = 5
            elif 0.5 <= med_ret5d < 2.0: f2 = round((med_ret5d - 0.5) / 1.5 * 12)
            elif -2.0 <= med_ret5d < 0.5: f2 = 2
            else: f2 = 0
            score += f2

            # F3: Breadth (25 pts) = 1D (15 pts) + 5D (10 pts)
            f3a = 15 if breadth_1d >= 75 else (12 if breadth_1d >= 60 else (7 if breadth_1d >= 50 else (3 if breadth_1d >= 40 else 0)))
            f3b = 10 if breadth_5d >= 70 else (7 if breadth_5d >= 55 else (3 if breadth_5d >= 40 else 0))
            score += (f3a + f3b)

            # F4: Trend Setup (20 pts) = MA20 (12 pts) + MA50 (8 pts)
            f4a = 12 if above_ma_pct >= 70 else (8 if above_ma_pct >= 50 else (3 if above_ma_pct >= 30 else 0))
            f4b = 8 if above_ma50_pct >= 70 else (5 if above_ma50_pct >= 50 else (2 if above_ma50_pct >= 30 else 0))
            score += (f4a + f4b)

            # F5: Persistence 20D (10 pts)
            f5 = 10 if med_ret20d >= 8 else (8 if med_ret20d >= 5 else (5 if med_ret20d >= 2 else (3 if med_ret20d >= 0 else 0)))
            score += f5

            # VPAI & Money Flow Bonus/Penalty
            up_vol_sum = sum(s["rvol"] for s in stock_metrics if s.get("ret_1d", 0) > 0)
            tot_vol_sum = sum(s["rvol"] for s in stock_metrics)
            up_vol_ratio = (up_vol_sum / tot_vol_sum) if tot_vol_sum > 0 else 0.5
            if up_vol_ratio >= 0.65: score += 5
            elif up_vol_ratio < 0.40: score -= 15

            # Sharpe Adjusted Momentum
            ret5d_std = float(np.std(ret5d_vals)) if len(ret5d_vals) > 1 else 1.0
            sharpe_mom_5d = med_ret5d / max(0.5, ret5d_std)
            if sharpe_mom_5d >= 1.5 and med_ret5d > 1.0: score += 5
            elif sharpe_mom_5d < -1.5 and med_ret5d < -1.0: score -= 10

            # SPY RS
            rs_20d = med_ret20d - spy_ret20
            if rs_20d >= 8.0: score += 5
            elif rs_20d < -8.0: score -= 10

            # Alignment
            if ma_align_pct >= 60: score += 5
            elif ma_align_pct < 20: score -= 10

            if med_ret60d > 40: score -= 20
            elif med_ret60d > 30: score -= 10
            if med_ret20d < -8 and med_ret5d > 3: score -= 15

            quality = max(0, min(100, score))
            prev_sig = self.prev_signals.get(tid, "NOISE")
            is_true_prev = (prev_sig == "TRUE_SIGNAL")
            is_watch_prev = (prev_sig == "WATCH" or prev_sig == "TRUE_SIGNAL")

            req_quality_true = 60 if is_true_prev else 70
            req_breadth_true = 45.0 if is_true_prev else 50.0
            req_breadth5d_true = 40.0 if is_true_prev else 45.0
            req_ma_true = 45.0 if is_true_prev else 55.0
            req_ret5d_true = 0.8 if is_true_prev else 1.2

            is_deadcat = (med_ret20d < -8 and med_ret5d > 3)
            is_pump = (med_ret5d > 8 and breadth_1d < 35 and med_rvol > 1.5)
            is_overheated = (med_ret60d > 35 and med_ret5d > 5)
            is_breakdown = (above_ma_pct < 25.0 and med_ret20d < -5.0 and up_vol_ratio < 0.35)

            if is_deadcat: sig_type = "DEAD_CAT"
            elif is_pump: sig_type = "PUMP"
            elif is_overheated: sig_type = "OVERHEATED"
            elif is_breakdown: sig_type = "BREAKDOWN"
            elif (quality >= req_quality_true and breadth_1d >= req_breadth_true and
                  breadth_5d >= req_breadth5d_true and above_ma_pct >= req_ma_true and
                  med_ret5d >= req_ret5d_true and med_ret20d >= -2.0 and up_vol_ratio >= 0.45):
                sig_type = "TRUE_SIGNAL"
            elif quality >= (35 if is_watch_prev else 40) and med_rvol >= 0.5 and (med_ret5d >= 0.5 or breadth_5d >= 35.0):
                sig_type = "WATCH"
            else:
                sig_type = "NOISE"

            name_ko = self.themes_config.get(tid, {}).get("name_ko", tid)
            name_en = self.themes_config.get(tid, {}).get("name_en", tid)

            results.append({
                "theme_id": tid, "name_ko": name_ko, "name_en": name_en,
                "stock_count": n, "med_rvol": round(med_rvol, 2),
                "med_ret1d": round(med_ret1d, 2), "med_ret5d": round(med_ret5d, 2),
                "med_ret20d": round(med_ret20d, 2), "med_ret60d": round(med_ret60d, 2),
                "ret_1d": round(med_ret1d, 2), "ret_5d": round(med_ret5d, 2),
                "ret_20d": round(med_ret20d, 2), "ret_60d": round(med_ret60d, 2),
                "breadth_1d": round(breadth_1d, 1), "breadth_5d": round(breadth_5d, 1),
                "above_ma_pct": round(above_ma_pct, 1), "above_ma50_pct": round(above_ma50_pct, 1),
                "ma_align_pct": round(ma_align_pct, 1), "quality": quality,
                "signal_type": sig_type, "stock_data": stock_metrics,
            })

        df = pd.DataFrame(results).sort_values("quality", ascending=False).reset_index(drop=True)
        
        # Save to DB & Cache
        from update_signals_batch import save_signals_to_db
        save_signals_to_db(df)
        
        try:
            with open(CACHE_JSON, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Failed to dump cache: {}", e)

        elapsed_sec = time.time() - cycle_start
        true_cnt = sum(1 for r in results if r["signal_type"] == "TRUE_SIGNAL")
        watch_cnt = sum(1 for r in results if r["signal_type"] == "WATCH")
        
        # Heartbeat status dump
        status = {
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "cycle_duration_sec": round(elapsed_sec, 2),
            "market_state": m_state,
            "themes_count": len(results),
            "true_signals_count": true_cnt,
            "watch_signals_count": watch_cnt
        }
        with open(STATUS_JSON, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2)

        # 🚨 Broadcast Telegram Golden Cross Alerts
        self.broadcast_golden_cross_alerts(results)

        logger.info("Cycle completed in {:.1f}s | 🟢 TRUE: {} | 🟡 WATCH: {} | Total Themes: {}",
                    elapsed_sec, true_cnt, watch_cnt, len(results))

    def broadcast_golden_cross_alerts(self, current_results: List[Dict[str, Any]]):
        """Sends instant Telegram card when a theme transitions into TRUE_SIGNAL."""
        try:
            tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
            tg_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
            if not tg_token or not tg_chat_id:
                for candidate in [
                    os.path.join(os.path.dirname(BASE_DIR), "kis-auto-trading", ".env"),
                    "/home/ubuntu/kis-auto-trading/.env",
                    ".env"
                ]:
                    if os.path.exists(candidate):
                        with open(candidate, "r", encoding="utf-8") as ef:
                            for line in ef:
                                if line.startswith("TELEGRAM_BOT_TOKEN="):
                                    tg_token = line.split("=", 1)[1].strip().strip('"').strip("'")
                                elif line.startswith("TELEGRAM_CHAT_ID="):
                                    tg_chat_id = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if tg_token and tg_chat_id:
                            break

            if not tg_token or not tg_chat_id:
                return

            # 1. 🛑 Ironclad Weekend & Off-Market Hours Silence Guard (100% Silent on Weekends/Off-Hours)
            tz = pytz.timezone('US/Eastern')
            now_est = datetime.datetime.now(tz)
            if now_est.weekday() >= 5:
                logger.info("Weekend in US (ET: {}). Theme push alerts are 100% silenced.", now_est.strftime("%A %H:%M"))
                return

            current_minutes = now_est.hour * 60 + now_est.minute
            if not (9 * 60 + 30 <= current_minutes < 16 * 60):
                logger.info("Off-market hours in US (ET: {}). Theme push alerts are 100% silenced.", now_est.strftime("%H:%M"))
                return

            m_state = get_market_state()
            if m_state != "REGULAR":
                logger.info("Market is not in REGULAR trading (State: {}). Skipping theme alerts.", m_state)
                return

            # 2. SQLite Persisted 24-Hour Alert Cooldown
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS theme_alerts_history (
                        theme_id TEXT PRIMARY KEY,
                        sent_at REAL,
                        quality INTEGER,
                        rvol REAL
                    )
                """)
                conn.commit()
                conn.close()
            except Exception:
                pass

            now_ts = time.time()
            new_true = set()
            alerts_sent_this_cycle = 0

            # Sort current results by quality descending
            true_candidates = [r for r in current_results if r.get("signal_type") == "TRUE_SIGNAL"]
            true_candidates.sort(key=lambda x: x.get("quality", 0), reverse=True)

            # Record all current true themes
            for r in true_candidates:
                new_true.add(r.get("theme_id"))

            prev_true = getattr(self, "prev_true_themes", set())

            # 3. Only evaluate Elite TOP 3 Themes (Quality >= 90, RVOL >= 1.5x, Breadth >= 70%)
            for rank_idx, r in enumerate(true_candidates[:3], 1):
                tid = r.get("theme_id")
                quality = r.get("quality", 0)
                rvol = r.get("med_rvol", 1.0)
                breadth = r.get("breadth_1d", 0.0)

                # Ultra-Elite Hurdle: Quality >= 90, RVOL >= 1.5x, Breadth >= 70%
                if quality < 90 or rvol < 1.50 or breadth < 70.0:
                    continue

                # State Transition: Only alert on NEW breakout (NOISE/WATCH -> TRUE_SIGNAL)
                # OR if 24 hours have passed since last alert
                last_sent = 0
                try:
                    conn = sqlite3.connect(DB_PATH)
                    row = conn.execute("SELECT sent_at FROM theme_alerts_history WHERE theme_id = ?", (tid,)).fetchone()
                    if row:
                        last_sent = float(row[0])
                    conn.close()
                except Exception:
                    last_sent = 0

                # 24-Hour Cooldown per theme
                if now_ts - last_sent < 24 * 3600:
                    continue

                # Must be a newly emerged breakout OR top 1 rank
                if tid in prev_true and rank_idx > 1 and (now_ts - last_sent < 24 * 3600):
                    continue

                # Max 1 alert per cycle to prevent clutter
                if alerts_sent_this_cycle >= 1:
                    break

                name_ko = r.get("name_ko", tid)
                ret_5d = r.get("ret_5d", 0.0)

                rec_lines = []
                try:
                    conn = sqlite3.connect(DB_PATH)
                    cur = conn.cursor()
                    cur.execute("SELECT ticker, pick_type, price, target_price, stop_loss, target_pct, stop_pct FROM theme_recommendations WHERE theme_id = ?", (tid,))
                    for p_row in cur.fetchall():
                        rec_lines.append(f"  • <b>{p_row[0]}</b> ({p_row[1]}): ${p_row[2]:.2f} ➔ 🎯목표가 ${p_row[3]:.2f} (+{p_row[5]:.1f}%) | 🛡️손절가 ${p_row[4]:.2f} (-{p_row[6]:.1f}%)")
                    conn.close()
                except Exception:
                    pass

                msg_lines = [
                    "🚨 <b>[주도 테마 기관 수급 폭발 포착 (TOP 1% 초정예)]</b>",
                    "━━━━━━━━━━━━━━━━━━━",
                    f"📡 <b>주도 테마 (랭킹 {rank_idx}위):</b> <code>[{name_ko}]</code>",
                    f"⭐️ <b>신호:</b> 🟢 <b>TRUE_SIGNAL</b> (퀀트 품질: <b>{quality}점</b>)",
                    f"⚡️ <b>기관 수급:</b> RVOL <b>{rvol:.2f}x</b> | 브레드스 <b>{breadth:.1f}%</b> | 5D {ret_5d:+0.1f}%\n",
                    "🏆 <b>[실시간 퀀트 1픽 주도주]</b>"
                ]
                if rec_lines:
                    msg_lines.extend(rec_lines)
                else:
                    msg_lines.append("  • <i>종목 산출 중</i>")
                msg_lines.append("━━━━━━━━━━━━━━━━━━━")
                msg_lines.append("💡 <i>초정예 수급 폭발로 자동매매 봇의 1순위 매수 풀에 즉시 편입되었습니다.</i>")

                card_text = "\n".join(msg_lines)
                import requests
                requests.post(
                    f"https://api.telegram.org/bot{tg_token}/sendMessage",
                    json={"chat_id": tg_chat_id, "text": card_text, "parse_mode": "HTML"},
                    timeout=5
                )

                # Save to SQLite history
                try:
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute("INSERT OR REPLACE INTO theme_alerts_history (theme_id, sent_at, quality, rvol) VALUES (?, ?, ?, ?)",
                                 (tid, now_ts, quality, rvol))
                    conn.commit()
                    conn.close()
                except Exception:
                    pass

                alerts_sent_this_cycle += 1
                logger.info("Sent Elite Golden Cross Telegram alert for theme: {} (Quality: {}, Rank: {})", name_ko, quality, rank_idx)

            self.prev_true_themes = new_true
        except Exception as e:
            logger.debug("Golden cross alert error: {}", e)

    def start(self):
        logger.info("Starting Theme Radar 24/7 Autonomous Daemon...")
        while True:
            try:
                m_state = get_market_state()
                self.run_cycle()
                import gc
                gc.collect()
                
                # Dynamic sleep interval based on market hours (5 mins during trading)
                if m_state == "REGULAR":
                    sleep_sec = 300  # Every 5 minutes in regular trading
                elif m_state == "EXTENDED":
                    sleep_sec = 600  # Every 10 minutes in pre/post market
                else:
                    sleep_sec = 1800 # Every 30 minutes outside market hours/weekends
                    
                logger.info("Sleeping for {}s until next cycle...", sleep_sec)
                time.sleep(sleep_sec)
            except KeyboardInterrupt:
                logger.info("Daemon stopped by user.")
                break
            except Exception as e:
                logger.error("Unexpected error in daemon cycle: {}\n{}", e, traceback.format_exc())
                time.sleep(30)

if __name__ == "__main__":
    daemon = ThemeRadarDaemon()
    daemon.start()
