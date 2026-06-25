import os
import json
import sqlite3
import datetime
import numpy as np
import pandas as pd
import yfinance as yf

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
THEME_DB_JSON = os.path.join(BASE_DIR, "theme_db.json")
DB_PATH = os.path.join(BASE_DIR, "us_stocks_data.db")

def get_volume_scale_factor(last_date_str):
    """
    미국 동부 시간(US/Eastern) 기준으로 당일 개장 시간(09:30~16:00) 동안의 경과 시간을 계산하여,
    당일 실시간 거래량을 하루 전체 예상 거래량으로 보정하기 위한 배율(Scale Factor)을 반환합니다.
    """
    import pytz
    import datetime
    
    tz = pytz.timezone('US/Eastern')
    now_est = datetime.datetime.now(tz)
    today_est_str = now_est.strftime("%Y-%m-%d")
    
    # 마지막 데이터 날짜가 오늘 날짜가 아니면 (즉, 아직 오늘 봉이 생성되지 않았거나 어제 봉인 경우) -> 보정 안 함
    if last_date_str != today_est_str:
        return 1.0
        
    current_minutes = now_est.hour * 60 + now_est.minute
    open_minutes = 9 * 60 + 30  # 09:30 -> 570
    close_minutes = 16 * 60     # 16:00 -> 960
    
    # 장 개장 전이거나 장이 마감된 이후 -> 보정 안 함
    if current_minutes < open_minutes or current_minutes >= close_minutes:
        return 1.0
        
    # 장중: 경과 시간을 분 단위로 계산 (최소 15분으로 제한하여 장 초반 극단적인 튐 방지)
    elapsed = float(current_minutes - open_minutes)
    elapsed = max(15.0, elapsed)
    
    return 390.0 / elapsed

THEME_CATEGORIES = {
    "🤖 AI & 반도체": [
        "custom_ai_chips","nand_memory","dram_memory","optical_interconnects",
        "ai_networking_switches","server_manufacturers","gpu_cloud_infrastructure",
        "hyperscale_cloud","ai_software_enterprise","lithography_equipment",
        "etching_deposition_equipment","semiconductor_wafers","power_semiconductors",
        "analog_mixed_signal","fpga_chips","rf_mobile_chips","semiconductor_test_equipment",
        "eda_ip_software","chip_packaging_osat","contract_foundry",
        "quantum_computing","generative_ai_platforms","devops_observability",
        "vector_databases","digital_twin","cdn_edge_networking","crm_enterprise_saas",
        "enterprise_networking","five_g_telecom_equipment",
    ],
    "⚡ 에너지 & 전력": [
        "power_generation_equipment","power_grid_transformers","datacenter_liquid_cooling",
        "smr_nuclear","uranium_mining","nuclear_utilities","solar_panels","solar_inverters",
        "wind_energy","hydrogen_fuel_cells","grid_scale_batteries","solid_state_batteries",
        "geothermal_energy","gas_turbines","carbon_capture",
    ],
    "🛸 방산 & 우주": [
        "hypersonic_missiles","unmanned_systems","space_launch_vehicles","satellite_communications",
        "defense_electronics","shipbuilding_naval","directed_energy_weapons",
    ],
    "🤖 로보틱스 & 모빌리티": [
        "industrial_robotics","warehouse_automation","autonomous_driving_lidar","ev_chargers",
        "ev_batteries","advanced_air_mobility","commercial_ev",
    ],
    "🧬 헬스케어 & 바이오": [
        "mrna_vaccines","crispr_gene_editing","cell_immunotherapy","glp_one_obesity",
        "radiopharmaceuticals","robotic_surgery","genomic_sequencing","telehealth_platform",
        "alzheimers_therapeutics",
    ],
    "💎 소재 & 자원": [
        "rare_earth_metals","lithium_mining","copper_mining","specialty_chemicals_gases",
        "water_infrastructure","construction_materials",
    ],
    "📺 소비자 & 미디어": [
        "e_commerce_logistics","food_delivery_mobility","digital_advertising","ota_travel",
        "e_sports_gaming","streaming_media","cybersecurity_platforms","fintech_payments",
        "bnpl_lending","restaurants_food","retail_stores","apparel_footwear",
    ],
    "🏦 금융": [
        "regional_banks","insurance","asset_management","reits_real_estate","datacenter_reits",
    ],
    "📡 통신": ["telecom_carriers","cable_broadband","air_freight_logistics"],
}

def db_query(sql, params=()):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        conn.close()

def save_signals_to_db(df: pd.DataFrame):
    """실시간 연산된 테마 신호 및 원픽 추천 종목을 SQLite DB에 영구 기록하여 자동매매봇과 연동"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS theme_signals (
                theme_id TEXT PRIMARY KEY,
                name_ko TEXT,
                signal_type TEXT,
                quality INTEGER,
                med_rvol REAL,
                ret_5d REAL,
                updated_at TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS theme_recommendations (
                ticker TEXT PRIMARY KEY,
                theme_id TEXT,
                pick_type TEXT,
                price REAL,
                target_price REAL,
                stop_loss REAL,
                target_pct REAL,
                stop_pct REAL,
                updated_at TEXT
            )
        """)
        
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("DELETE FROM theme_recommendations")
        
        for _, row in df.iterrows():
            tid = row["theme_id"]
            cur.execute("""
                INSERT INTO theme_signals (theme_id, name_ko, signal_type, quality, med_rvol, ret_5d, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(theme_id) DO UPDATE SET
                    signal_type=excluded.signal_type,
                    quality=excluded.quality,
                    med_rvol=excluded.med_rvol,
                    ret_5d=excluded.ret_5d,
                    updated_at=excluded.updated_at
            """, (tid, row["name_ko"], row["signal_type"], row["quality"], row["med_rvol"], row["ret_5d"], now_str))
            
            if row["signal_type"] not in ["TRUE_SIGNAL", "WATCH"]:
                continue
                
            scored_stocks = []
            tickers_list = [s["ticker"] for s in row["stock_data"]]
            
            db_meta = {}
            if tickers_list:
                placeholders = ",".join(["?"] * len(tickers_list))
                cur.execute(f"SELECT ticker, name FROM stock_metadata WHERE ticker IN ({placeholders})", tuple(tickers_list))
                rows = cur.fetchall()
                db_meta = {r[0]: {"name": r[1]} for r in rows}
                
            for s in row["stock_data"]:
                t = s["ticker"]
                rvol = s["rvol"]
                ret_5d = s["ret_5d"]
                ret_20d = s["ret_20d"]
                ret_1d = s["ret_1d"]
                price = s["price"]
                daily_vol = s.get("daily_vol", 2.0)
                
                meta = db_meta.get(t, {})
                name = meta.get("name") or t
                
                score = 0
                if rvol >= 2.5: score += 35
                elif rvol >= 1.8: score += 30
                elif rvol >= 1.3: score += 20
                elif rvol >= 1.0: score += 10
                
                if 2.0 <= ret_5d <= 7.0: score += 35
                elif 7.0 < ret_5d <= 12.0: score += 20
                elif 0.5 <= ret_5d < 2.0: score += 25
                elif ret_5d > 12.0: score += 5
                
                if ret_20d >= 0: score += 20
                elif -5.0 <= ret_20d < 0: score += 10
                
                if ret_1d > 0: score += 10
                if ret_20d > 25.0: score -= 30
                
                scored_stocks.append({
                    "ticker": t, "name": name, "price": price, "ret_5d": ret_5d, "daily_vol": daily_vol, "score": score
                })
                
            if scored_stocks:
                scored_stocks.sort(key=lambda x: x["score"], reverse=True)
                leader = scored_stocks[0]
                
                # Leader Pick
                if leader["score"] >= 40:
                    vol = leader["daily_vol"]
                    stop_pct = max(3.0, min(12.0, vol * 1.5))
                    target_pct = max(6.0, min(30.0, vol * 3.5))
                    
                    cur.execute("""
                        INSERT INTO theme_recommendations 
                        (ticker, theme_id, pick_type, price, target_price, stop_loss, target_pct, stop_pct, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(ticker) DO UPDATE SET
                            theme_id=excluded.theme_id,
                            pick_type=excluded.pick_type,
                            price=excluded.price,
                            target_price=excluded.target_price,
                            stop_loss=excluded.stop_loss,
                            target_pct=excluded.target_pct,
                            stop_pct=excluded.stop_pct,
                            updated_at=excluded.updated_at
                    """, (leader["ticker"], tid, "LEADER", leader["price"], 
                          round(leader["price"] * (1 + target_pct/100), 2),
                          round(leader["price"] * (1 - stop_pct/100), 2),
                          round(target_pct, 1), round(stop_pct, 1), now_str))
                          
                # Setup Pick
                setups = [s for s in scored_stocks if s["ticker"] != leader["ticker"]]
                if setups:
                    setup_candidates = [s for s in setups if -3.0 <= s["ret_5d"] <= 3.0]
                    if setup_candidates:
                        setup_pick = setup_candidates[0]
                        vol = setup_pick["daily_vol"]
                        stop_pct = max(2.5, min(10.0, vol * 1.2))
                        target_pct = max(5.0, min(25.0, vol * 2.8))
                        
                        cur.execute("""
                            INSERT INTO theme_recommendations 
                            (ticker, theme_id, pick_type, price, target_price, stop_loss, target_pct, stop_pct, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(ticker) DO UPDATE SET
                                theme_id=excluded.theme_id,
                                pick_type=excluded.pick_type,
                                price=excluded.price,
                                target_price=excluded.target_price,
                                stop_loss=excluded.stop_loss,
                                target_pct=excluded.target_pct,
                                stop_pct=excluded.stop_pct,
                                updated_at=excluded.updated_at
                        """, (setup_pick["ticker"], tid, "SETUP", setup_pick["price"], 
                              round(setup_pick["price"] * (1 + target_pct/100), 2),
                              round(setup_pick["price"] * (1 - stop_pct/100), 2),
                              round(target_pct, 1), round(stop_pct, 1), now_str))
        conn.commit()
    except Exception as e:
        print(f"Error saving theme signals to DB: {e}")
    finally:
        conn.close()

def main():
    print(f"[{datetime.datetime.now()}] Batch calculation started...")
    
    if not os.path.exists(THEME_DB_JSON):
        print(f"Theme DB configuration file not found at {THEME_DB_JSON}")
        return
        
    with open(THEME_DB_JSON, "r", encoding="utf-8") as f:
        themes_config = json.load(f).get("themes", {})
        
    theme_tickers = {}
    for tid, cfg in themes_config.items():
        pm = cfg.get("premapped_tickers", [])
        rows = db_query("SELECT ticker FROM stock_metadata WHERE theme_tags LIKE ?", (f"%{tid}%",))
        db_ticks = [r[0] for r in rows]
        all_ticks = list(dict.fromkeys(pm + db_ticks))[:30]
        if len(all_ticks) >= 2:
            theme_tickers[tid] = all_ticks
            
    if not theme_tickers:
        print("No active theme tickers found.")
        return
        
    all_unique = list(dict.fromkeys(t for ticks in theme_tickers.values() for t in ticks))
    chunk_size = 150
    import time

    print(f"Downloading daily historical prices for {len(all_unique)} tickers in chunks of {chunk_size}...")
    daily_chunks = []
    for i in range(0, len(all_unique), chunk_size):
        chunk = all_unique[i:i+chunk_size]
        try:
            time.sleep(0.3)
            raw_c = yf.download(chunk, period="3mo", interval="1d", auto_adjust=True, progress=False, threads=True, group_by="ticker")
            if not raw_c.empty:
                daily_chunks.append(raw_c)
        except Exception as e:
            print(f"Error downloading daily chunk {i}: {e}")

    if daily_chunks:
        raw_daily = pd.concat(daily_chunks, axis=1)
    else:
        raw_daily = pd.DataFrame()
        
    if raw_daily.empty:
        print("Daily data is empty.")
        return

    print(f"Downloading live pre-market prices for {len(all_unique)} tickers in chunks of {chunk_size}...")
    live_chunks = []
    for i in range(0, len(all_unique), chunk_size):
        chunk = all_unique[i:i+chunk_size]
        try:
            time.sleep(0.3)
            raw_l = yf.download(chunk, period="1d", interval="1m", prepost=True, progress=False, threads=True, group_by="ticker")
            if not raw_l.empty:
                live_chunks.append(raw_l)
        except Exception as e:
            print(f"Error downloading live chunk {i}: {e}")

    if live_chunks:
        raw_live = pd.concat(live_chunks, axis=1)
    else:
        raw_live = pd.DataFrame()
        
    def get_series(df, ticker, col):
        try:
            if isinstance(df.columns, pd.MultiIndex):
                return df[ticker][col].dropna()
            else:
                return df[col].dropna() if col in df.columns else pd.Series(dtype=float)
        except Exception:
            return pd.Series(dtype=float)

    # Load previous signal_types for hysteresis (prevents signal flickering)
    prev_signals = {}
    try:
        rows = db_query("SELECT theme_id, signal_type FROM theme_signals")
        prev_signals = {r[0]: r[1] for r in rows}
    except Exception as e:
        print(f"Warning: could not load previous signals for hysteresis: {e}")

    results = []
    for tid, ticks in theme_tickers.items():
        stock_metrics = []
        for t in ticks:
            c = get_series(raw_daily, t, "Close")
            v = get_series(raw_daily, t, "Volume")
            if len(c) < 22:
                continue

            ret_1d  = float((c.iloc[-1]/c.iloc[-2]-1)*100)  if len(c)>=2  else 0.0
            ret_5d  = float((c.iloc[-1]/c.iloc[-6]-1)*100)  if len(c)>=6  else ret_1d
            ret_20d = float((c.iloc[-1]/c.iloc[-21]-1)*100) if len(c)>=21 else ret_5d
            ret_60d = float((c.iloc[-1]/c.iloc[0]-1)*100)   if len(c)>=60 else ret_20d

            if len(v) >= 21:
                # 🎯 Apply Time-Weighted Volume Projection
                last_date_str = v.index[-1].strftime("%Y-%m-%d")
                scale_factor = get_volume_scale_factor(last_date_str)
                
                today_v = float(v.iloc[-1]) * scale_factor
                avg_v   = float(v.iloc[-21:-1].mean())
                rvol    = today_v / avg_v if avg_v > 0 else 1.0
            else:
                rvol = 1.0

            daily_returns = c.iloc[-21:].pct_change().dropna()
            daily_vol = float(daily_returns.std() * 100) if len(daily_returns) > 0 else 2.0

            ma20 = float(c.iloc[-20:].mean()) if len(c)>=20 else float(c.iloc[-1])
            ma50 = float(c.iloc[-50:].mean()) if len(c)>=50 else float(c.iloc[-1])
            above_ma20 = bool(c.iloc[-1] > ma20)
            above_ma50 = bool(c.iloc[-1] > ma50)

            # 프리마켓 실시간 주가 추출
            live_c = get_series(raw_live, t, "Close")
            if not raw_live.empty and len(live_c) > 0:
                live_price = float(live_c.iloc[-1])
            else:
                live_price = float(c.iloc[-1])

            stock_metrics.append({
                "ret_1d": ret_1d, "ret_5d": ret_5d,
                "ret_20d": ret_20d, "ret_60d": ret_60d,
                "rvol": rvol, "above_ma20": above_ma20, "above_ma50": above_ma50,
                "is_up_1d": bool(ret_1d > 0),
                "price": live_price,
                "ticker": t,
                "daily_vol": round(daily_vol, 2),
            })

        n = len(stock_metrics)
        if n == 0:
            continue

        med_rvol   = float(np.median([s["rvol"]   for s in stock_metrics]))
        med_ret1d  = float(np.median([s["ret_1d"] for s in stock_metrics]))
        med_ret5d  = float(np.median([s["ret_5d"] for s in stock_metrics]))
        med_ret20d = float(np.median([s["ret_20d"] for s in stock_metrics]))
        med_ret60d = float(np.median([s["ret_60d"] for s in stock_metrics]))

        breadth_1d = sum(s["is_up_1d"] for s in stock_metrics) / n * 100
        above_ma_pct   = sum(s["above_ma20"] for s in stock_metrics) / n * 100
        above_ma50_pct = sum(s["above_ma50"] for s in stock_metrics) / n * 100
        up_5d = sum(s["ret_5d"] > 0 for s in stock_metrics) / n * 100

        score = 0
        if med_rvol >= 2.5:   f1 = 30
        elif med_rvol >= 1.8: f1 = 25
        elif med_rvol >= 1.4: f1 = 18
        elif med_rvol >= 1.1: f1 = 8
        else:                  f1 = 0
        score += f1

        if 2.0 <= med_ret5d <= 5.0:   f2 = 25
        elif 5.0 < med_ret5d <= 10.0: f2 = 15
        elif med_ret5d > 10.0:        f2 = 5
        elif 0.5 <= med_ret5d < 2.0:  f2 = 10
        elif -2.0 <= med_ret5d < 0.5: f2 = 2
        else:                          f2 = 0
        score += f2

        if breadth_1d >= 75:   f3 = 25
        elif breadth_1d >= 60: f3 = 20
        elif breadth_1d >= 50: f3 = 12
        elif breadth_1d >= 40: f3 = 6
        else:                   f3 = 0
        score += f3

        if above_ma_pct >= 70:   f4 = 15
        elif above_ma_pct >= 50: f4 = 10
        elif above_ma_pct >= 30: f4 = 4
        else:                     f4 = 0
        score += f4

        if med_ret20d >= 5:    f5 = 5
        elif med_ret20d >= 0:  f5 = 3
        elif med_ret20d >= -5: f5 = 1
        else:                   f5 = 0
        score += f5

        if med_ret60d > 30:  score -= 10
        if med_ret20d < -8 and med_ret5d > 3:  score -= 15

        quality = max(0, min(100, score))

        prev_sig = prev_signals.get(tid, "NOISE")
        
        # Define Hysteresis (Buffer) Thresholds
        is_true_prev = (prev_sig == "TRUE_SIGNAL")
        is_watch_prev = (prev_sig == "WATCH" or prev_sig == "TRUE_SIGNAL")
        
        req_quality_true = 60 if is_true_prev else 70
        req_rvol_true    = 1.4 if is_true_prev else 1.6
        req_breadth_true = 50.0 if is_true_prev else 60.0
        req_ma_true      = 50.0 if is_true_prev else 60.0
        req_ma50_true    = 40.0 if is_true_prev else 50.0
        req_ret5d_true   = 1.0 if is_true_prev else 1.5
        
        req_quality_watch = 35 if is_watch_prev else 40
        req_rvol_watch    = 1.0 if is_watch_prev else 1.1
        req_ret5d_watch   = 0.8 if is_watch_prev else 1.0

        is_deadcat = (med_ret20d < -8 and med_ret5d > 3)
        is_pump    = (med_ret5d > 8 and breadth_1d < 35 and med_rvol > 1.5)
        is_overheated = (med_ret60d > 30 and med_ret5d > 5)

        if is_deadcat:
            sig_type = "DEAD_CAT"
        elif is_pump:
            sig_type = "PUMP"
        elif is_overheated:
            sig_type = "OVERHEATED"
        elif (quality >= req_quality_true and 
              med_rvol >= req_rvol_true and 
              breadth_1d >= req_breadth_true and 
              above_ma_pct >= req_ma_true and 
              above_ma50_pct >= req_ma50_true and 
              med_ret5d >= req_ret5d_true):
            sig_type = "TRUE_SIGNAL"
        elif (quality >= req_quality_watch and 
              (med_rvol >= req_rvol_watch or med_ret5d >= req_ret5d_watch)):
            sig_type = "WATCH"
        else:
            sig_type = "NOISE"

        name_ko = themes_config.get(tid, {}).get("name_ko", tid)
        name_en = themes_config.get(tid, {}).get("name_en", tid)

        cat = "🔹 기타"
        for c_name, c_tids in THEME_CATEGORIES.items():
            if tid in c_tids:
                cat = c_name
                break

        is_vol_breakout = bool(med_rvol >= 1.5 and med_ret1d > 0.5 and sig_type == "TRUE_SIGNAL")
        is_trnd_breakout = bool(above_ma_pct >= 50.0 and -6.0 <= med_ret20d <= 6.0 and med_ret5d > 1.0 and sig_type == "TRUE_SIGNAL")

        if med_ret1d > 0 and med_ret5d > 0 and med_rvol >= 1.2:
            velocity_icon = "▲ 가속"
        elif med_ret1d < 0 and med_ret5d < 0:
            velocity_icon = "▼ 감속"
        else:
            velocity_icon = "▬ 유지"

        results.append({
            "theme_id":    tid,
            "name_ko":     name_ko,
            "name_en":     name_en,
            "category":    cat,
            "stock_count": n,
            "med_rvol":    round(med_rvol, 2),
            "ret_1d":      round(med_ret1d, 2),
            "ret_5d":      round(med_ret5d, 2),
            "ret_20d":     round(med_ret20d, 2),
            "ret_60d":     round(med_ret60d, 2),
            "breadth_1d":  round(breadth_1d, 1),
            "above_ma_pct":round(above_ma_pct, 1),
            "above_ma50_pct":round(above_ma50_pct, 1),
            "up_5d_pct":   round(up_5d, 1),
            "quality":     quality,
            "signal_type": sig_type,
            "factors":     {"rvol": f1, "momentum": f2, "breadth": f3, "trend": f4, "persistence": f5},
            "stock_data":  stock_metrics,
            "is_volume_breakout": is_vol_breakout,
            "is_trend_breakout":  is_trnd_breakout,
            "velocity_icon":      velocity_icon,
        })

    df = pd.DataFrame(results)
    df = df.sort_values("quality", ascending=False).reset_index(drop=True)
    
    print("Writing signals to database...")
    save_signals_to_db(df)
    
    # JSON 캐시 파일 덤프 (대시보드 0.1초 로딩용)
    cache_path = os.path.join(BASE_DIR, "theme_radar_cache.json")
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print("Successfully dumped theme_radar_cache.json")
    except Exception as cache_err:
        print(f"Failed to dump JSON cache: {cache_err}")
        
    print(f"[{datetime.datetime.now()}] Batch calculation completed successfully.")

if __name__ == "__main__":
    main()
