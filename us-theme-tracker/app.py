"""
app.py - US Stock Theme Radar v4.0
실전 매매용 퀀트 신호 대시보드
- 실시간 yfinance 데이터 기반 (캐시 없는 신선한 가격)
- 5-factor 신호 품질 엔진 (RVOL, 모멘텀, 브레스, 추세, 일관성)
- 테마 클릭 → 상세 종목 드릴다운
- 완전 인터랙티브 UI
"""
import os, json, sqlite3, datetime, warnings
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf

warnings.filterwarnings("ignore")

DB_PATH      = "us_stocks_data.db"
THEME_DB_JSON = "theme_db.json"

# ════════════════════════════════════════════════════════════
# PAGE CONFIG
# ════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="US Theme Radar",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ════════════════════════════════════════════════════════════
# CSS
# ════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
html, body, [class*="css"] { font-family:'Inter',sans-serif; }
.stApp { background:#080e18; color:#d0dff0; }

/* Scrollbar Customization */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #060c16; }
::-webkit-scrollbar-thumb { background: #1a2e4a; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #2a5090; }

/* Sidebar */
section[data-testid="stSidebar"]>div { background:#060c16!important; border-right:1px solid #1a2840; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background:#0d1625; border-radius:10px; padding:4px; gap:4px; border:1px solid #1a2840; }
.stTabs [data-baseweb="tab"] { border-radius:8px; color:#6a8fbb; font-weight:500; padding:8px 18px; }
.stTabs [aria-selected="true"] { background:linear-gradient(135deg,#1a3a6a,#1e4a8a)!important; color:#e6f3ff!important; }

/* Metric cards */
.metric-card {
    background:linear-gradient(135deg,#0d1825,#111f35);
    border:1px solid #1a2e4a;
    border-radius:12px;
    padding:18px 20px;
    transition:all 0.2s ease;
}
.metric-card:hover { border-color:#2a5090; transform:translateY(-1px); box-shadow:0 4px 20px rgba(42,80,144,0.3); }

/* Signal cards - clickable */
.sig-card {
    border-radius:10px;
    padding:14px 18px;
    margin-bottom:8px;
    cursor:pointer;
    transition:all 0.15s ease;
    border-left:4px solid;
}
.sig-card:hover { transform:translateX(4px); filter:brightness(1.1); }

.sig-true  { background:linear-gradient(135deg,#041a0c,#061f10); border-color:#00d97e; }
.sig-watch { background:linear-gradient(135deg,#181004,#1c1404); border-color:#f0b429; }
.sig-fake  { background:linear-gradient(135deg,#180408,#1c0408); border-color:#ff3b5c; }

/* Badges */
.badge { display:inline-block; padding:3px 9px; border-radius:20px; font-size:11px; font-weight:700; margin:2px; }
.b-green  { background:#00d97e18; color:#00d97e; border:1px solid #00d97e44; }
.b-yellow { background:#f0b42918; color:#f0b429; border:1px solid #f0b42944; }
.b-red    { background:#ff3b5c18; color:#ff3b5c; border:1px solid #ff3b5c44; }
.b-blue   { background:#3a9bdc18; color:#3a9bdc; border:1px solid #3a9bdc44; }
.b-gray   { background:#2a3a4a; color:#7aa3cc; border:1px solid #3a5070; }
.b-purple { background:#8b5cf618; color:#a78bfa; border:1px solid #8b5cf644; }

/* Ticker chip */
.chip { display:inline-block; background:#0a1e35; border:1px solid #1a3a5c; color:#7ab8f5;
        padding:3px 9px; border-radius:5px; font-family:'JetBrains Mono',monospace;
        font-size:12px; margin:2px; font-weight:600; }

/* Quality bar */
.qbar-bg { background:#1a2840; border-radius:4px; height:6px; width:100%; }
.qbar    { border-radius:4px; height:6px; }

/* Detail panel */
.detail-panel {
    background:linear-gradient(135deg,#0a1520,#0d1d30);
    border:1px solid #1e3a5f;
    border-radius:12px;
    padding:24px;
    margin-top:12px;
}

/* Alert box */
.alert-buy {
    background:linear-gradient(135deg,#021208,#031a0c);
    border:2px solid #00d97e;
    border-radius:12px;
    padding:20px 24px;
    margin-bottom:20px;
}

/* Table rows */
.trow-g { color:#00d97e; font-weight:700; }
.trow-r { color:#ff3b5c; font-weight:700; }

/* Streamlit Button Premium Override */
div.stButton > button {
    background: linear-gradient(135deg, #0d1e36, #142b4d) !important;
    color: #e6f3ff !important;
    border: 1px solid #1e3a6e !important;
    border-radius: 8px !important;
    padding: 8px 16px !important;
    font-weight: 600 !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    width: 100%;
}
div.stButton > button:hover {
    background: linear-gradient(135deg, #163563, #1e467a) !important;
    border-color: #3a75c4 !important;
    box-shadow: 0 4px 15px rgba(58,117,196,0.3) !important;
    transform: translateY(-1px) !important;
}
div.stButton > button:active {
    transform: translateY(0px) !important;
}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# THEME CONFIG
# ════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600)
def load_themes_config():
    if os.path.exists(THEME_DB_JSON):
        with open(THEME_DB_JSON, "r", encoding="utf-8") as f:
            return json.load(f).get("themes", {})
    return {}

themes_config = load_themes_config()

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
        "lng_natural_gas","pipeline_midstream","oil_gas_exploration","carbon_capture",
    ],
    "🛸 방산 & 우주": [
        "commercial_space_launch","satellite_communication","uav_defense_drones",
        "defense_primes","hypersonic_tech","evtol_flying_cars",
    ],
    "🧬 헬스케어 & 바이오": [
        "glp1_weight_loss","crispr_gene_editing","mrna_therapies","cart_immunotherapy",
        "liquid_biopsy","surgical_robotics","medical_aesthetics","telehealth",
        "microbiome_health","medical_devices_general","diagnostics_lab_instruments",
        "contract_research_cro","genomics_sequencing","alzheimers_neuro","oncology_targeted",
        "pharmaceuticals_traditional",
    ],
    "🪙 크립토 & 핀테크": [
        "bitcoin_proxies","crypto_miners","payments_fintech","bnpl_lending_fintech",
        "trading_brokerage",
    ],
    "🤖 로보틱스 & 모빌리티": [
        "humanoid_robotics","warehouse_automation","autonomous_driving",
        "three_d_printing","industrial_automation","auto_manufacturers",
    ],
    "💎 소재 & 자원": [
        "copper_mining","lithium_mining","rare_earth_elements","steel_metals",
        "specialty_chemicals","construction_materials","solid_waste_recycling","water_infrastructure",
    ],
    "📺 소비자 & 미디어": [
        "streaming_media_ott","social_media_platforms","digital_advertising_adtech",
        "ecommerce_marketplace","food_delivery_rideshare","online_travel",
        "online_gaming_esports","sports_betting","cannabis",
        "restaurants_food","retail_stores","apparel_footwear",
    ],
    "🏦 금융": [
        "regional_banks","insurance","asset_management","reits_real_estate","datacenter_reits",
    ],
    "📡 통신": ["telecom_carriers","cable_broadband","air_freight_logistics"],
}

# ════════════════════════════════════════════════════════════
# DB HELPERS
# ════════════════════════════════════════════════════════════
def db_query(sql, params=()):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        conn.close()

def db_df(sql, params=()):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()

# ════════════════════════════════════════════════════════════
# MARKET REGIME FILTER (지수 연동 시장 위험 신호등)
# ════════════════════════════════════════════════════════════
@st.cache_data(ttl=900)
def get_market_regime():
    """나스닥 100(QQQ)과 S&P 500(SPY)의 실시간 상태를 분석하여 시장 국면 판단"""
    try:
        raw = yf.download(["SPY", "QQQ"], period="3mo", auto_adjust=True, progress=False)
        if raw.empty:
            return "🟢 SAFE (적극 매수)", "시장 데이터를 로드할 수 없어 기본 '안전' 상태로 설정합니다.", "#00d97e", 0.0, 0.0
        
        close = raw["Close"]
        
        # QQQ 지표 계산
        c_qqq = close["QQQ"].dropna()
        ma20_qqq = c_qqq.iloc[-20:].mean()
        ma50_qqq = c_qqq.iloc[-50:].mean()
        curr_qqq = c_qqq.iloc[-1]
        
        # SPY 지표 계산
        c_spy = close["SPY"].dropna()
        ma20_spy = c_spy.iloc[-20:].mean()
        ma50_spy = c_spy.iloc[-50:].mean()
        curr_spy = c_spy.iloc[-1]
        
        # 5일 모멘텀 계산
        ret_5d_qqq = (c_qqq.iloc[-1] / c_qqq.iloc[-6] - 1) * 100
        ret_5d_spy = (c_spy.iloc[-1] / c_spy.iloc[-6] - 1) * 100
        
        # 상태 판별
        if curr_qqq > ma20_qqq and curr_spy > ma20_spy:
            status = "🟢 SAFE (적극 매수 국면)"
            desc = "나스닥과 S&P500 지수가 모두 중기 이평선(MA20) 위에 안착한 강세장입니다. 적극적인 테마 매매가 가능합니다."
            color = "#00d97e"
        elif curr_qqq < ma50_qqq and curr_spy < ma50_spy:
            status = "🔴 RISK (현금 확보 / 매수 금지)"
            desc = "지수가 장기 하락 지지선(MA50)마저 이탈한 약세장입니다. 동반 하락 위험이 극도로 크니 신규 매수를 금지하고 현금 비중을 늘리십시오."
            color = "#ff3b5c"
        else:
            status = "🟡 CAUTION (보수적/분할 진입)"
            desc = "지수가 단기 조정 국면(MA20 이탈 및 지지선 모색)에 있습니다. 매매 비중을 50% 이하로 줄이고 분할 매수로 보수적인 대응을 권장합니다."
            color = "#f0b429"
            
        return status, desc, color, round(ret_5d_qqq, 2), round(ret_5d_spy, 2)
    except Exception as e:
        return "🟢 SAFE (적극 매수 국면)", f"국면 분석 오류({e})로 임시 SAFE 설정.", "#00d97e", 0.0, 0.0


# ════════════════════════════════════════════════════════════
# REAL-TIME SIGNAL ENGINE (yfinance 기반)
# ════════════════════════════════════════════════════════════
def fetch_live_prices(tickers: list, period="3mo") -> pd.DataFrame:
    """yfinance에서 실시간 가격 가져오기"""
    if not tickers:
        return pd.DataFrame()
    try:
        raw = yf.download(
            tickers, period=period,
            auto_adjust=True, progress=False, threads=True
        )
        if raw.empty:
            return pd.DataFrame()

        if isinstance(raw.columns, pd.MultiIndex):
            close = raw["Close"]
            volume = raw["Volume"]
        else:
            close = raw[["Close"]]
            volume = raw[["Volume"]]
            close.columns = tickers[:1]
            volume.columns = tickers[:1]

        return close, volume
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame()


def compute_stock_metrics(close_df: pd.DataFrame, volume_df: pd.DataFrame, ticker: str):
    """단일 종목 퀀트 지표 계산"""
    if ticker not in close_df.columns:
        return None
    c = close_df[ticker].dropna()
    v = volume_df[ticker].dropna() if ticker in volume_df.columns else pd.Series(dtype=float)

    if len(c) < 22:
        return None

    cur_price  = float(c.iloc[-1])
    ret_1d     = float((c.iloc[-1] / c.iloc[-2] - 1) * 100) if len(c) >= 2 else 0.0
    ret_5d     = float((c.iloc[-1] / c.iloc[-6] - 1) * 100) if len(c) >= 6 else ret_1d
    ret_20d    = float((c.iloc[-1] / c.iloc[-21] - 1) * 100) if len(c) >= 21 else ret_5d

    # RVOL: today vs 20-day avg (excluding today)
    if len(v) >= 21:
        today_vol = float(v.iloc[-1])
        avg_vol   = float(v.iloc[-21:-1].mean())
        rvol = today_vol / avg_vol if avg_vol > 0 else 1.0
    else:
        rvol = 1.0

    return {
        "ticker": ticker,
        "price": round(cur_price, 2),
        "ret_1d": round(ret_1d, 2),
        "ret_5d": round(ret_5d, 2),
        "ret_20d": round(ret_20d, 2),
        "rvol": round(rvol, 2),
    }


def save_signals_to_db(df: pd.DataFrame):
    """실시간 연산된 테마 신호 및 원픽 추천 종목을 SQLite DB에 영구 기록하여 자동매매봇과 연동"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()
    try:
        # 1. 테이블 생성
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
        
        # 이전 추천 데이터 삭제
        cur.execute("DELETE FROM theme_recommendations")
        
        for _, row in df.iterrows():
            tid = row["theme_id"]
            
            # 테마 신호 UPSERT
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
            
            # 탑픽 계산 및 저장 (TRUE_SIGNAL 또는 WATCH 테마만 추천 등록)
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


def get_cache_mtime():
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "theme_radar_cache.json")
    if os.path.exists(cache_path):
        return os.path.getmtime(cache_path)
    return 0


def sync_from_vps():
    key_file = r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading\id_rsa"
    if not os.path.exists(key_file):
        return False
        
    import subprocess
    ip = "141.148.172.12"
    user = "ubuntu"
    local_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "us_stocks_data.db")
    local_cache = os.path.join(os.path.dirname(os.path.abspath(__file__)), "theme_radar_cache.json")
    
    remote_db = "/home/ubuntu/us-theme-tracker/us_stocks_data.db"
    remote_cache = "/home/ubuntu/us-theme-tracker/theme_radar_cache.json"
    
    known_hosts_dev = "NUL" if os.name == "nt" else "/dev/null"
    
    try:
        # Pull cache json with 30s timeout
        res_cache = subprocess.run(
            ['scp', '-i', key_file, 
             '-o', 'StrictHostKeyChecking=no', 
             '-o', f'UserKnownHostsFile={known_hosts_dev}', 
             f'{user}@{ip}:{remote_cache}', local_cache],
            capture_output=True, text=True, timeout=30
        )
        
        # Pull DB with 60s timeout
        res_db = subprocess.run(
            ['scp', '-i', key_file, 
             '-o', 'StrictHostKeyChecking=no', 
             '-o', f'UserKnownHostsFile={known_hosts_dev}', 
             f'{user}@{ip}:{remote_db}', local_db],
            capture_output=True, text=True, timeout=60
        )
        
        if res_cache.returncode == 0 and res_db.returncode == 0:
            return True
        else:
            print(f"Sync failed. Cache code={res_cache.returncode}, DB code={res_db.returncode}")
            print(f"Cache Stderr: {res_cache.stderr}")
            print(f"DB Stderr: {res_db.stderr}")
            return False
    except Exception as e:
        print(f"Failed to sync from VPS: {e}")
        return False


@st.cache_data(ttl=900, show_spinner=False)   # 15분 캐시
def compute_theme_signals(max_themes=80, force_refresh=False, cache_mtime=0):
    """
    ★ 가속화 캐시 신호 엔진 ★
    update_signals_batch.py가 생성한 JSON 캐시를 0.1초 만에 불러옵니다.
    로컬 환경의 경우, VPS로부터 최신 시그널 및 가격 DB/캐시를 즉시 동기화(Sync)합니다.
    """
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "theme_radar_cache.json")
    key_file = r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading\id_rsa"
    
    run_local_batch = False
    
    # 1. 로컬 환경 확인 및 동기화 처리
    if os.path.exists(key_file):
        should_sync = force_refresh or not os.path.exists(cache_path)
        if not should_sync and os.path.exists(cache_path):
            import time
            mtime = os.path.getmtime(cache_path)
            # 마지막 동기화 후 10분이 경과했으면 자동으로 동기화
            if time.time() - mtime > 600:
                should_sync = True
                
        if should_sync:
            with st.spinner("🔄 VPS로부터 최신 퀀트 시그널 및 실시간 주가 동기화 중..."):
                success = sync_from_vps()
                if success:
                    st.toast("✅ VPS 동기화 성공!", icon="🟢")
                    st.cache_data.clear()
                else:
                    st.toast("⚠️ VPS 동기화 실패. 로컬 연산을 구동합니다.", icon="🟡")
                    run_local_batch = True
    else:
        # 키가 없는 원격 VPS 자체 환경 또는 순수 로컬인 경우
        if force_refresh or not os.path.exists(cache_path):
            run_local_batch = True
            
    # 2. 로컬 배치 구동 (동기화 실패 혹은 로컬 전용 실행 시)
    if run_local_batch:
        with st.spinner("📡 실시간 퀀트 시그널 연산 중... (yfinance 대용량 다운로드로 약 30초 소요)"):
            import subprocess
            import sys
            batch_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "update_signals_batch.py")
            python_bin = sys.executable
            real_python = r"C:\Users\wngud\AppData\Local\Python\bin\python.exe"
            if os.path.exists(real_python):
                python_bin = real_python
            elif "WindowsApps" in python_bin or "PythonSoftwareFoundation" in python_bin:
                python_bin = "python"
            try:
                subprocess.run([python_bin, batch_script], check=True)
                st.cache_data.clear()
            except Exception as e:
                st.error(f"실시간 배치 구동 실패: {e}")
                
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                results = json.load(f)
            if results:
                df = pd.DataFrame(results)
                df = df.sort_values("quality", ascending=False).reset_index(drop=True)
                return df
        except Exception as e:
            st.error(f"캐시 파일 파싱 오류: {e}")
            
    return pd.DataFrame()


def _render_theme_detail(tid, theme_row_df, cfg, tab_name="detail"):
    """테마 상세 정보 렌더링 - 신호 상태, 팩터 분석, 종목 테이블, 차트"""
    if theme_row_df.empty:
        st.warning("해당 테마의 신호 데이터가 없습니다.")
        return

    row = theme_row_df.iloc[0]
    sig_type = row["signal_type"]
    sig_color = {"TRUE_SIGNAL":"#00d97e","WATCH":"#f0b429",
                 "DEAD_CAT":"#ff3b5c","PUMP":"#ff3b5c","OVERHEATED":"#f0b429"}.get(sig_type,"#7aa3cc")
    sig_label_map = {"TRUE_SIGNAL":"✅ 진짜신호 — 진입 가능","WATCH":"⚠️ 관찰중 — 눌림목 대기",
                     "DEAD_CAT":"💀 데드캣 바운스 — 매수 금지","PUMP":"🔴 투기적 펌핑 — 트랩",
                     "OVERHEATED":"🌡️ 과열 — 차익실현 구간","NOISE":"⚫ 신호 없음"}
    sig_text = sig_label_map.get(sig_type, "미분류")

    f = row["factors"]

    st.markdown(f"""
    <div class="detail-panel">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:16px;">
        <div>
          <div style="color:{sig_color};font-size:15px;font-weight:700;">{sig_text}</div>
          <div style="color:#7aa3cc;font-size:13px;margin-top:4px;">{cfg.get('description','')}</div>
          <div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;">
            <span class="badge b-gray">{row['stock_count']}개 종목</span>
            <span class="badge b-gray">{row.get('category','')}</span>
          </div>
        </div>
        <div style="display:flex;gap:12px;flex-wrap:wrap;">
    """, unsafe_allow_html=True)

    # Metric boxes
    metrics = [
        ("1일", row["ret_1d"], "%"),
        ("5일", row["ret_5d"], "%"),
        ("20일", row["ret_20d"], "%"),
        ("RVOL", row["med_rvol"], "x"),
        ("브레스", row["breadth_1d"], "%"),
    ]
    boxes = ""
    for label, val, unit in metrics:
        c = "#00d97e" if val >= 0 else "#ff3b5c"
        sign = "+" if val >= 0 and label != "RVOL" and label != "브레스" else ""
        boxes += f"""
        <div style="background:#0a1a30;border-radius:8px;padding:10px 14px;text-align:center;min-width:80px;">
          <div style="color:#7aa3cc;font-size:10px;">{label}</div>
          <div style="color:{c};font-size:18px;font-weight:700;">{sign}{val:.1f}{unit}</div>
        </div>"""
    st.markdown(boxes + "</div></div>", unsafe_allow_html=True)

    # Factor breakdown
    st.markdown("#### 📊 5-Factor 신호 분해")
    factor_data = [
        ("🔊 거래량 RVOL",  f["rvol"],        30, "#00d97e", f"RVOL {row['med_rvol']:.2f}x (30점 만점)"),
        ("📈 모멘텀",       f["momentum"],     25, "#3a9bdc", f"5일 수익 {row['ret_5d']:+.1f}% (25점 만점)"),
        ("🫁 브레스",       f["breadth"],      25, "#a78bfa", f"오늘 양봉 {row['breadth_1d']:.0f}% (25점 만점)"),
        ("📐 추세",         f["trend"],        15, "#f0b429", f"MA20 위 {row['above_ma_pct']:.0f}% (15점 만점)"),
        ("⏱ 지속성",       f["persistence"],   5, "#fb923c", f"20일 흐름 {row['ret_20d']:+.1f}% (5점 만점)"),
    ]
    total_score = sum(x[1] for x in factor_data)
    for label, score, max_score, color, desc in factor_data:
        pct = score / max_score * 100 if max_score > 0 else 0
        st.markdown(f"""
        <div style="margin-bottom:6px;">
          <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px;">
            <span style="color:#c9d1d9;">{label}</span>
            <span style="color:{color};font-weight:700;">{score}/{max_score}</span>
          </div>
          <div class="qbar-bg"><div class="qbar" style="width:{pct:.0f}%;background:{color};"></div></div>
          <div style="color:#5a7a9a;font-size:11px;margin-top:1px;">{desc}</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background:#0a1520;border-radius:8px;padding:10px 14px;margin-top:8px;text-align:right;margin-bottom:20px;">
      <span style="color:#7aa3cc;font-size:12px;">합계: </span>
      <span style="color:#{'00d97e' if total_score>=65 else 'f0b429' if total_score>=40 else 'ff3b5c'};
                  font-size:20px;font-weight:800;">{total_score}점 / 100점</span>
    </div>
    """, unsafe_allow_html=True)

    # ─── 🎯 퀀트 탑픽 추천 알고리즘 ───────────────────────
    tickers_list = [s["ticker"] for s in row["stock_data"]]
    db_meta = {}
    if tickers_list:
        placeholders = ",".join(["?"] * len(tickers_list))
        rows = db_query(f"SELECT ticker, name, industry FROM stock_metadata WHERE ticker IN ({placeholders})", tuple(tickers_list))
        db_meta = {r[0]: {"name": r[1], "industry": r[2]} for r in rows}

    scored_stocks = []
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
        industry = meta.get("industry") or ""
        
        # 종목별 퀀트 점수
        score = 0
        # 1. 수급 (RVOL): 거래량 급증 최고 35점
        if rvol >= 2.5: score += 35
        elif rvol >= 1.8: score += 30
        elif rvol >= 1.3: score += 20
        elif rvol >= 1.0: score += 10
        
        # 2. 5일 수익률: 적당한 초입 상승 최고 35점 (너무 안 올랐거나 너무 급등한 건 제외)
        if 2.0 <= ret_5d <= 7.0: score += 35
        elif 7.0 < ret_5d <= 12.0: score += 20
        elif 0.5 <= ret_5d < 2.0: score += 25
        elif ret_5d > 12.0: score += 5  # 과열 패널티
        
        # 3. 20일 중기 추세 (양수 전환 = 정배열 지지) 최고 20점
        if ret_20d >= 0: score += 20
        elif -5.0 <= ret_20d < 0: score += 10
        
        # 4. 1일 당일 양봉 수급 최고 10점
        if ret_1d > 0: score += 10
        
        # 과열 추격 방지 패널티
        if ret_20d > 25.0: score -= 30
        
        scored_stocks.append({
            "ticker": t, "name": name, "industry": industry, "price": price,
            "ret_1d": ret_1d, "ret_5d": ret_5d, "ret_20d": ret_20d, "rvol": rvol,
            "daily_vol": daily_vol, "score": score
        })

    top_picks = []
    if scored_stocks:
        scored_df = pd.DataFrame(scored_stocks).sort_values("score", ascending=False)
        
        # 1. 주도주 원픽 (1위)
        leader = scored_df.iloc[0]
        if leader["score"] >= 40:
            price = leader["price"]
            vol = leader["daily_vol"]
            
            # 동적 익절/손절 비율 계산 (1.5x, 3.5x 일일 변동성 표준편차 기반)
            # 최소/최대 안전 가드 작동
            stop_pct = max(3.0, min(12.0, vol * 1.5))
            target_pct = max(6.0, min(30.0, vol * 3.5))
            
            target_price = price * (1 + target_pct / 100)
            stop_loss = price * (1 - stop_pct / 100)
            
            top_picks.append({
                "type": "🔥 주도 수급 원픽 (Leader Pick)",
                "ticker": leader["ticker"],
                "name": leader["name"],
                "price": price,
                "ret_5d": leader["ret_5d"],
                "rvol": leader["rvol"],
                "color": "#00d97e",
                "bg": "rgba(0, 217, 126, 0.15)",
                "target_price": round(target_price, 2),
                "stop_loss": round(stop_loss, 2),
                "target_pct": round(target_pct, 1),
                "stop_pct": round(stop_pct, 1),
                "reason": f"최근 5일간 {leader['ret_5d']:+.1f}%의 안정적 탄력성을 보이고 있으며, 평소 대비 거래량이 {leader['rvol']:.1f}배 급증하여 수급이 뚜렷합니다. 일일 변동성 {vol:.1f}%를 반영한 맞춤 익절가(+{target_pct:.1f}%)와 손절가(-{stop_pct:.1f}%)로 설계되었습니다."
            })
            
        # 2. 눌림목 원픽
        setups = scored_df[scored_df["ticker"] != leader["ticker"]]
        if not setups.empty:
            setup_candidates = setups[setups["ret_5d"].between(-3.0, 3.0)]
            if not setup_candidates.empty:
                setup_pick = setup_candidates.iloc[0]
                price = setup_pick["price"]
                vol = setup_pick["daily_vol"]
                
                # 눌림목은 상대적으로 좁은 진폭 (1.2x, 2.8x 표준편차 기반)
                stop_pct = max(2.5, min(10.0, vol * 1.2))
                target_pct = max(5.0, min(25.0, vol * 2.8))
                
                target_price = price * (1 + target_pct / 100)
                stop_loss = price * (1 - stop_pct / 100)
                
                top_picks.append({
                    "type": "💤 눌림목 분할매수 원픽 (Setup Pick)",
                    "ticker": setup_pick["ticker"],
                    "name": setup_pick["name"],
                    "price": price,
                    "ret_5d": setup_pick["ret_5d"],
                    "rvol": setup_pick["rvol"],
                    "color": "#3a9bdc",
                    "bg": "rgba(58, 155, 220, 0.15)",
                    "target_price": round(target_price, 2),
                    "stop_loss": round(stop_loss, 2),
                    "target_pct": round(target_pct, 1),
                    "stop_pct": round(stop_pct, 1),
                    "reason": f"테마 상승세 속에 최근 단기 숨고르기({setup_pick['ret_5d']:+.1f}%)를 거쳤고, 20일선 부근 지지를 받습니다. 일일 변동성 {vol:.1f}%를 반영하여 손익비가 극대화된 익절가(+{target_pct:.1f}%) 및 손절가(-{stop_pct:.1f}%)를 제공합니다."
                })

    # 탑픽 렌더링
    if top_picks:
        st.markdown("#### 🎯 퀀트 원픽 추천 종목")
        cols = st.columns(len(top_picks))
        for idx, pick in enumerate(top_picks):
            with cols[idx]:
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#0a1b30,#102545);
                            border:1px solid #1e3a6e;border-radius:10px;padding:16px;height:100%;box-shadow:0 4px 15px rgba(0,0,0,0.4);">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                    <span style="font-size:11px;font-weight:700;padding:2px 8px;border-radius:20px;
                                 background:{pick['bg']};color:{pick['color']};border:1px solid {pick['color']}44;">
                      {pick['type'].split('(')[0]}
                    </span>
                    <span style="font-family:'JetBrains Mono',monospace;font-size:18px;font-weight:800;color:#e6f3ff;">
                      {pick['ticker']}
                    </span>
                  </div>
                  <div style="font-size:14px;font-weight:600;color:#7ab8f5;margin-bottom:6px;">{pick['name'][:25]}</div>
                  <div style="font-size:18px;font-weight:700;color:{pick['color']};margin-bottom:8px;">
                    ${pick['price']:.2f} 
                    <span style="font-size:12px;color:#7aa3cc;">(5일: {pick['ret_5d']:+.1f}%, RVOL: {pick['rvol']:.1f}x)</span>
                  </div>
                  <!-- 목표가/손절가 추가 -->
                  <div style="background:rgba(0,0,0,0.2);border-radius:6px;padding:8px 10px;margin-bottom:8px;border:1px solid #1d3557;">
                    <div style="color:#00d97e;font-weight:700;font-size:13px;margin-bottom:2px;">
                      🎯 익절 목표가: ${pick['target_price']:.2f} (+{pick['target_pct']}%)
                    </div>
                    <div style="color:#ff3b5c;font-weight:700;font-size:13px;">
                      🛑 손절 대응가: ${pick['stop_loss']:.2f} (-{pick['stop_pct']}%)
                    </div>
                  </div>
                  <div style="font-size:12px;color:#a0c4e8;line-height:1.6;margin-top:8px;">{pick['reason']}</div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # ─── 🎯 세부 종목 실시간 히트맵 (Treemap) ───────────────────────
    if scored_stocks:
        st.markdown("#### 🗺️ 세부 종목 실시간 히트맵 (타일 크기 = 거래량(RVOL) 강도 ⚡)")
        detail_tree_df = pd.DataFrame(scored_stocks)
        # RVOL은 0 이하가 될 수 없으나, Plotly Treemap의 안전한 렌더링을 위해 최소값 0.1 부여
        detail_tree_df["weight"] = detail_tree_df["rvol"].apply(lambda x: max(0.1, x))
        detail_tree_df["label"] = detail_tree_df.apply(lambda r: f"{r['ticker']}<br>{r['ret_5d']:+.1f}%<br>({r['rvol']:.1f}x)", axis=1)
        
        fig_detail_tree = px.treemap(
            detail_tree_df,
            path=["label"],
            values="weight",
            color="ret_5d",
            color_continuous_scale=["#ff3b5c", "#1a2840", "#00d97e"],
            color_continuous_midpoint=0,
            hover_data={"price": ":.2f", "ret_5d": ":+.1f%", "rvol": ":.2f}x"},
        )
        fig_detail_tree.update_layout(
            paper_bgcolor="#080e18", plot_bgcolor="#080e18",
            font={"color": "#c9d1d9", "family": "Inter"},
            coloraxis_colorbar=dict(title="5D%", tickfont=dict(color="#7aa3cc")),
            margin=dict(l=0, r=0, t=10, b=0), height=250
        )
        fig_detail_tree.update_traces(
            textfont=dict(color="white", size=11, family="JetBrains Mono"),
            marker_line_width=1, marker_line_color="#0d1520"
        )
        st.plotly_chart(fig_detail_tree, use_container_width=True, key=f"detail_tree_{tab_name}_{tid}")
        st.markdown("<br>", unsafe_allow_html=True)

    # 📋 종목 성과 테이블 렌더링
    st.markdown("#### 📋 종목별 성과")
    display_df = pd.DataFrame(scored_stocks)
    if display_df.empty:
        st.info("해당 테마에 매핑된 종목 정보가 없습니다.")
    else:
        display = display_df.copy()
        display["1일"] = display["ret_1d"].map(lambda x: f"{x:+.2f}%")
        display["5일"] = display["ret_5d"].map(lambda x: f"{x:+.2f}%")
        display["20일"] = display["ret_20d"].map(lambda x: f"{x:+.2f}%")
        display["RVOL"] = display["rvol"].map(lambda x: f"{x:.2f}x")
        display["가격"] = display["price"].map(lambda x: f"${x:,.2f}")

        st.dataframe(
            display[["ticker","name","industry","가격","1일","5일","20일","RVOL"]].rename(
                columns={"ticker":"종목","name":"회사명","industry":"업종"}
            ),
            use_container_width=True,
            hide_index=True,
            height=min(35 * len(display) + 50, 450),
        )

        # 미니 바 차트
        if len(display_df) >= 2:
            fig2 = go.Figure(go.Bar(
                x=display_df["ticker"],
                y=display_df["ret_5d"],
                marker_color=display_df["ret_5d"].apply(lambda x: "#00d97e" if x >= 0 else "#ff3b5c"),
                text=display_df["ret_5d"].apply(lambda x: f"{x:+.1f}%"),
                textposition="outside",
            ))
            fig2.update_layout(
                paper_bgcolor="#080e18", plot_bgcolor="#0d1625",
                font={"color":"#c9d1d9","family":"Inter"},
                height=220, margin=dict(l=0,r=0,t=20,b=0),
                xaxis=dict(gridcolor="#1a2840", tickfont=dict(color="#7ab8f5", family="JetBrains Mono", size=11)),
                yaxis=dict(gridcolor="#1a2840", ticksuffix="%", tickfont=dict(color="#7aa3cc")),
                showlegend=False,
            )
            st.plotly_chart(fig2, use_container_width=True, key=f"plotly_{tab_name}_{tid}")

    st.markdown("</div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
# SESSION STATE INIT
# ════════════════════════════════════════════════════════════
if "selected_theme_tab1" not in st.session_state:
    st.session_state.selected_theme_tab1 = None
if "selected_theme_tab2" not in st.session_state:
    st.session_state.selected_theme_tab2 = None
if "selected_theme_tab3" not in st.session_state:
    st.session_state.selected_theme_tab3 = None
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = None
if "trigger_force_refresh" not in st.session_state:
    st.session_state.trigger_force_refresh = False


# ════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════
now_kst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
st.markdown(f"""
<div style="background:linear-gradient(135deg,#0a1628,#0d1f3c,#0a1628);
            border:1px solid #1e3a5f;border-radius:14px;padding:22px 28px;margin-bottom:20px;">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div>
      <div style="font-size:26px;font-weight:800;color:#e6f3ff;">🎯 US Stock Theme Radar</div>
      <div style="color:#7aa3cc;font-size:13px;margin-top:4px;">
        퀀트 기반 세부테마 조기 포착 | 3,000+ 종목 | 5-Factor 실시간 신호 엔진
      </div>
    </div>
    <div style="text-align:right;">
      <div style="color:#00d97e;font-size:14px;font-weight:600;">● LIVE</div>
      <div style="color:#7aa3cc;font-size:12px;">KST {now_kst.strftime('%H:%M')}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# MARKET REGIME INDICATOR (시장 국면 표시기)
# ════════════════════════════════════════════════════════════
status, desc, color, qqq_5d, spy_5d = get_market_regime()
st.markdown(f"""
<div style="background:linear-gradient(135deg,#0d1f3c,#080e18);
            border:1px solid {color}44;border-radius:12px;padding:16px 20px;margin-bottom:20px;">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
    <div>
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
        <span style="color:{color};font-size:15px;font-weight:800;letter-spacing:0.5px;">🚦 {status}</span>
        <span class="badge b-purple">나스닥 5D: {qqq_5d:+.2f}%</span>
        <span class="badge b-blue">S&P500 5D: {spy_5d:+.2f}%</span>
      </div>
      <div style="color:#a0c4e8;font-size:12px;margin-top:6px;line-height:1.5;">{desc}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### ⚙️ 설정")

    show_traditional = st.toggle("전통 섹터 포함 (은행/보험/리츠)", value=False)
    min_stocks = st.slider("최소 종목 수", 1, 10, 3)

    st.markdown("---")
    auto_refresh = st.toggle("⏱️ 실시간 자동 갱신 (2분 주기)", value=True)
    if auto_refresh:
        import streamlit.components.v1 as components
        components.html(
            """
            <script>
                setTimeout(function(){
                    window.parent.location.reload();
                }, 120000);
            </script>
            """,
            height=0,
        )

    st.markdown("---")
    if st.button("🔄 신호 강제 갱신", use_container_width=True,
                 help="yfinance에서 최신 데이터 다시 로드"):
        st.cache_data.clear()
        st.session_state.trigger_force_refresh = True
        st.session_state.selected_theme_tab1 = None
        st.session_state.selected_theme_tab2 = None
        st.session_state.selected_theme_tab3 = None
        st.rerun()

    st.markdown("---")
    st.markdown("""
    <div style="font-size:12px;color:#7aa3cc;line-height:2.0;">
    <b>📖 5-Factor 신호 해석</b><br>
    거래량(RVOL) 최대 30점<br>
    모멘텀(5일 수익) 최대 25점<br>
    브레스(종목 일관성) 최대 25점<br>
    추세(MA20 위 비율) 최대 15점<br>
    지속성(20일 흐름) 최대 5점<br>
    <br>
    <b>기준:</b><br>
    🟢 65점+ & RVOL 1.4x+ & 브레스 50%+ = 진짜<br>
    ⚠️ 40점+ = 관찰<br>
    💀 20일-8% + 5일 반등 = 데드캣<br>
    🔴 5일 8%+ & 브레스 35%미만 = 펌핑
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:11px;color:#ffa6b4;line-height:1.7;background:#2a080c;border:1px solid #ff3b5c44;padding:10px;border-radius:8px;">
    <b>⚠️ 퀀트 매매 필수 유의사항</b><br>
    1. <b>실시간 가격 지연 안내</b><br>
    yfinance 무료 데이터 원천 특성상 미국 정규장 기준 <b>약 15분 내외의 주가 지연</b>이 있을 수 있습니다. 실제 호가 진입 시 반드시 증권사 실시간 매수창을 재확인하십시오.<br>
    <br>
    2. <b>모델 한계성 및 매수 자제 국면</b><br>
    지수 신호등이 🔴 RISK 국면(나스닥/S&P500이 50일 이동평균선 아래로 급락)일 때는, 개별 테마의 스코어가 아무리 높아도 시장 하방 압력으로 인해 오작동할 가능성이 현저히 높습니다. 지수가 무너질 땐 매매를 즉시 중단하십시오.
    </div>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
# LOAD DATA
# ════════════════════════════════════════════════════════════
TRADITIONAL = {"regional_banks","insurance","reits_real_estate","asset_management",
               "restaurants_food","retail_stores","pharmaceuticals_traditional",
               "steel_metals","auto_manufacturers","air_freight_logistics",
               "apparel_footwear","oil_gas_exploration","telecom_carriers","cable_broadband"}

cache_mtime = get_cache_mtime()

if st.session_state.get("trigger_force_refresh", False):
    raw_themes_df = compute_theme_signals(force_refresh=True, cache_mtime=cache_mtime)
    st.session_state.trigger_force_refresh = False
else:
    raw_themes_df = compute_theme_signals(force_refresh=False, cache_mtime=cache_mtime)

if raw_themes_df.empty:
    st.error("데이터 로드 실패. 인터넷 연결 및 종목 분류를 확인하세요.")
    st.stop()

# Apply filters to create filtered themes_df
themes_df = raw_themes_df.copy()
if not show_traditional:
    themes_df = themes_df[~themes_df["theme_id"].isin(TRADITIONAL)]
themes_df = themes_df[themes_df["stock_count"] >= min_stocks].reset_index(drop=True)

# Split by signal type
true_signals  = themes_df[themes_df["signal_type"] == "TRUE_SIGNAL"].head(10)
watch_signals = themes_df[themes_df["signal_type"] == "WATCH"].head(8)
# 위험 매수 금지 (과열/펌핑 등 진입 위험)
fake_signals  = themes_df[themes_df["signal_type"].isin(["PUMP", "OVERHEATED"])].head(6)
# 추세 이탈 / 즉시 매도 권장 (끝난 테마: 데드캣 또는 감속 + 음수수익률 + 저점수)
exit_signals  = themes_df[
    (themes_df["signal_type"] == "DEAD_CAT") | 
    ((themes_df["ret_5d"] < -1.5) & (themes_df["velocity_icon"] == "▼ 감속") & (themes_df["quality"] < 30))
].sort_values("ret_5d", ascending=True).head(6)

tab_signal, tab_board, tab_explorer = st.tabs(["🚨 실시간 매매 신호", "📊 전체 테마 순위", "🔍 테마 상세 탐색"])

with tab_signal:
    if status == "🚨 시장 폭락 국면":
        st.warning("⚠️ 시장 대폭락 위험 국면(QQQ/SPY 지수 장기이평선 이탈)이 감지되었습니다. 🟢 진입 가능 테마가 있어도 신규 매수를 보류하고 현금을 확보하는 것을 추천합니다. (시장이 무너질 때는 안전이 최선입니다.)")
    # ── TOP ALERT ──────────────────────────────────────────
    if not true_signals.empty:
        top = true_signals.iloc[0]
        f = top["factors"]
        st.markdown(f"""
        <div class="alert-buy">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
            <div>
              <div style="color:#7aa3cc;font-size:11px;font-weight:600;letter-spacing:1px;">⚡ 최강 진입 신호</div>
              <div style="color:#00d97e;font-size:26px;font-weight:800;margin:4px 0;">{top["name_ko"]}</div>
              <div style="color:#a0c4e8;font-size:13px;">{top["name_en"]}</div>
              <div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;">
                <span class="badge b-green">RVOL {top["med_rvol"]:.2f}x</span>
                <span class="badge b-green">5D +{top["ret_5d"]:.1f}%</span>
                <span class="badge b-blue">브레스 {top["breadth_1d"]:.0f}%</span>
                <span class="badge b-blue">추세 {top["above_ma_pct"]:.0f}%</span>
                <span class="badge b-gray">{top["stock_count"]}종목</span>
              </div>
            </div>
            <div style="text-align:center;background:#032010;border:1px solid #00d97e33;border-radius:12px;padding:16px 24px;">
              <div style="color:#00d97e;font-size:42px;font-weight:800;line-height:1;">{top["quality"]}</div>
              <div style="color:#7aa3cc;font-size:11px;margin-top:4px;">/ 100점</div>
              <div style="margin-top:8px;display:flex;gap:4px;font-size:10px;color:#7aa3cc;">
                <span>거래량:{f["rvol"]}</span>
                <span>모멘텀:{f["momentum"]}</span>
                <span>브레스:{f["breadth"]}</span>
                <span>추세:{f["trend"]}</span>
              </div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── 좌우 분할 듀얼 채널 레이아웃 적용 (스크롤 꼬임 방지 및 즉각 반응성 극대화) ──
    col_left, col_right = st.columns([5.5, 6.5], gap="large")

    with col_left:
        # 1. 즉시 진입 가능 테마
        st.markdown("### 🟢 즉시 진입 가능 테마")
        st.caption("극도의 퀀트 조건(Q 70점+, RVOL 1.6x+, 브레스 60%+, 정배열)을 충족한 진짜 신호")
        if true_signals.empty:
            st.info("현재 진입 조건 충족 테마 없음 — 관망 권장")
        else:
            for i, (_, row) in enumerate(true_signals.iterrows()):
                col_inner, col_meta = st.columns([3.5, 2.5])
                with col_inner:
                    if st.button(
                        f"🟢 {row['name_ko']} {row['velocity_icon']}",
                        key=f"sig_true_{i}",
                        use_container_width=True,
                    ):
                        st.session_state.selected_theme_tab1 = row["theme_id"]
                        st.rerun()
                with col_meta:
                    ret_c = "b-green" if row["ret_5d"] >= 0 else "b-red"
                    badges = f'<span class="badge b-blue">Q:{row["quality"]}</span> <span class="badge {ret_c}">{row["ret_5d"]:+.1f}%</span>'
                    if row["is_volume_breakout"]:
                        badges += ' <span class="badge b-purple">🔥수급폭발</span>'
                    st.markdown(
                        f'<div style="text-align:right;margin-top:4px;">{badges}</div>',
                        unsafe_allow_html=True
                    )

                # Factor bar 미니 시각화
                f = row["factors"]
                st.markdown(f"""
                <div style="display:flex;gap:2px;margin:-6px 0 12px 0;">
                  <div style="background:#00d97e;height:4px;width:{f['rvol']/30*100:.0f}%;border-radius:2px;" title="RVOL"></div>
                  <div style="background:#3a9bdc;height:4px;width:{f['momentum']/25*100:.0f}%;border-radius:2px;" title="모멘텀"></div>
                  <div style="background:#a78bfa;height:4px;width:{f['breadth']/25*100:.0f}%;border-radius:2px;" title="브레스"></div>
                  <div style="background:#f0b429;height:4px;width:{f['trend']/15*100:.0f}%;border-radius:2px;" title="추세"></div>
                  <div style="background:#fb923c;height:4px;width:{f['persistence']/5*100:.0f}%;border-radius:2px;" title="지속"></div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # 2. 관찰 대상 테마
        st.markdown("### ⚠️ 관찰 — 조건 충족 대기")
        st.caption("Q 40~69점 구간, 거래량 증가 및 조정 눌림목 대기")
        if watch_signals.empty:
            st.info("현재 관찰 대상 없음")
        else:
            for i, (_, row) in enumerate(watch_signals.iterrows()):
                clicked = st.button(
                    f"⚠️ {row['name_ko']} {row['velocity_icon']}  |  RVOL: {row['med_rvol']:.1f}x  |  5D: {row['ret_5d']:+.1f}%",
                    key=f"sig_watch_{i}",
                    use_container_width=True,
                )
                if clicked:
                    st.session_state.selected_theme_tab1 = row["theme_id"]
                    st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

        # 3. 위험 테마 (매수 금지)
        st.markdown("### 🔴 위험 — 매수 금지")
        st.caption("비동조 펌핑, 60일 과열 테마 감지 (진입 금지)")
        if fake_signals.empty:
            st.success("현재 감지된 진입 위험 테마 없음 ✅")
        else:
            for i, (_, row) in enumerate(fake_signals.iterrows()):
                label_map = {"PUMP":"⚠️ 투기펌핑","OVERHEATED":"🌡️ 과열"}
                label = label_map.get(row["signal_type"], "❌")
                clicked = st.button(
                    f"{label}  {row['name_ko']}  |  5D: {row['ret_5d']:+.1f}%",
                    key=f"sig_fake_{i}",
                    use_container_width=True,
                )
                if clicked:
                    st.session_state.selected_theme_tab1 = row["theme_id"]
                    st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

        # 4. 추세 이탈 / 즉시 매도 권장 (끝난 테마)
        st.markdown("### 📉 추세 이탈 / 매도 권장 (끝난 테마)")
        st.caption("데드캣 바운스, 거래량 급감 및 단기 하락 추세 전환 완료 테마 (보유 종목 청산 권장)")
        if exit_signals.empty:
            st.success("현재 감지된 매도 권장 테마 없음 ✅")
        else:
            for i, (_, row) in enumerate(exit_signals.iterrows()):
                label = "💀 데드캣" if row["signal_type"] == "DEAD_CAT" else "📉 추세이탈"
                clicked = st.button(
                    f"{label}  {row['name_ko']} {row['velocity_icon']}  |  5D: {row['ret_5d']:+.1f}%  |  Q: {row['quality']}점",
                    key=f"sig_exit_{i}",
                    use_container_width=True,
                )
                if clicked:
                    st.session_state.selected_theme_tab1 = row["theme_id"]
                    st.rerun()

    with col_right:
        st.markdown("### 🔍 퀀트 상세 분석 & 원픽 가이드")
        if st.session_state.selected_theme_tab1:
            tid = st.session_state.selected_theme_tab1
            cfg = themes_config.get(tid, {})
            theme_row = themes_df[themes_df["theme_id"] == tid]
 
            # 닫기 버튼 배치
            if st.button("✕ 상세분석 닫기", key="close_detail_tab1", use_container_width=True):
                st.session_state.selected_theme_tab1 = None
                st.rerun()
 
            _render_theme_detail(tid, theme_row, cfg, tab_name="tab1")
        else:
            st.markdown("""
            <div style="background:#0a1520;border:1px solid #1a3a5c;border-radius:12px;padding:48px 30px;text-align:center;margin-top:20px;">
               <div style="font-size:54px;margin-bottom:16px;">👈</div>
               <div style="color:#7ab8f5;font-weight:700;font-size:18px;margin-bottom:8px;">실시간 매매 신호 분석 대기 중</div>
               <div style="color:#a0c4e8;font-size:13px;line-height:1.6;">
                 왼쪽 목록에서 <b>[🟢 즉시 진입 가능]</b>, <b>[⚠️ 관찰]</b>, <b>[🔴 위험]</b>, 또는 <b>[📉 매도 권장]</b> 테마의 버튼을 클릭하십시오.<br>
                 해당 테마의 5-Factor 상세 분석 및 변동성 기반 익절/손절 추천 원픽 주도주 정보가 스크롤 없이 이곳에 즉시 출력됩니다.
               </div>
            </div>
            """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════
# TAB 2: 전체 순위표
# ════════════════════════════════════════════════════════════════════════
with tab_board:
    st.markdown("## 📊 전체 테마 순위표")
    
    # 실시간 세션 디버그 상태 출력 (우측 패널 활성화 상태 모니터링)
    st.markdown(f"""
    <div style="font-size:12px;color:#7aa3cc;margin-bottom:10px;">
      🖥️ Active Session: <b>{st.session_state.selected_theme_tab2 or "None (대기 중)"}</b>
    </div>
    """, unsafe_allow_html=True)

    # Interaction Guide Banner (Full-Width)
    st.markdown("""
    <div style="background:rgba(58,155,220,0.1);border:1px solid #3a9bdc44;border-radius:10px;padding:12px 16px;margin-bottom:16px;">
      <span style="color:#7ab8f5;font-weight:700;font-size:14px;">💡 실시간 조작 가이드</span>
      <div style="color:#a0c4e8;font-size:13px;margin-top:4px;line-height:1.5;">
        왼쪽 화면에서 <b>[히트맵 타일]</b>, <b>[가로 막대]</b>, 또는 <b>[테마 이름 버튼]</b>을 클릭하면, <b>오른쪽 화면에 상세 분석 및 원픽 종목 가이드가 즉시 노출</b>됩니다. <br>
        (화면 스크롤 없이 실시간 정보를 즉시 관찰할 수 있도록 듀얼 채널 레이아웃이 적용되었습니다.)
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Split Screen Layout: Left (Charts & List), Right (Details & Top Picks)
    col_left, col_right = st.columns([5.5, 6.5], gap="large")

    with col_left:
        # 1. Mega-Sectors Split Treemap (Tabs showing each theme)
        st.markdown("### 🗺️ 글로벌 섹터별 테마 히트맵 (전체 테마 분할 매핑)")
        
        mega_sectors = {
            "🤖 테크 & 디지털": [
                "🤖 AI & 반도체", "🪙 크립토 & 핀테크"
            ],
            "⚡ 제조 & 미래 산업": [
                "⚡ 에너지 & 전력", "🛸 방산 & 우주", "🤖 로보틱스 & 모빌리티"
            ],
            "🧬 헬스케어 & 바이오": [
                "🧬 헬스케어 & 바이오"
            ],
            "🏦 소비재 & 금융 & 자원": [
                "💎 소재 & 자원", "📺 소비자 & 미디어", "🏦 금융", "📡 통신"
            ]
        }
        
        def get_mega_sector(cat):
            for mega, categories in mega_sectors.items():
                if cat in categories:
                    return mega
            return "🔹 기타"
            
        # Explode raw_themes_df to stock-level for hierarchical Treemap (Category -> Theme -> Stock)
        flat_rows = []
        for _, row in raw_themes_df.iterrows():
            if row["stock_count"] < 1:
                continue
            mega = get_mega_sector(row["category"])
            for s in row["stock_data"]:
                flat_rows.append({
                    "mega_sector": mega,
                    "category": row["category"],
                    "name_ko": row["name_ko"],
                    "theme_id": row["theme_id"],
                    "ticker": s["ticker"],
                    "price": s["price"],
                    "ret_5d": s["ret_5d"],
                    "rvol": s["rvol"],
                    "label": f"{s['ticker']}<br>{s['ret_5d']:+.1f}%",
                    "weight": 1
                })
                
        if flat_rows:
            tree_data = pd.DataFrame(flat_rows)
        else:
            tree_data = pd.DataFrame()
            
        mega_list = list(mega_sectors.keys())
        
        # 4개의 큰분류를 가로 라디오 버튼으로 배치하여 가시성 문제 해결 및 스크롤 꼬임 해소
        selected_mega = st.radio(
            "📍 글로벌 섹터 대분류 선택 (클릭 시 하단 히트맵 즉시 전환)", 
            mega_list, 
            horizontal=True, 
            key="mega_sector_selector"
        )
        
        # mega_sectors에 매핑된 카테고리에 속한 테마들만 필터링
        selected_mega_categories = mega_sectors.get(selected_mega, [])
        mega_df = themes_df[themes_df["category"].isin(selected_mega_categories)].copy()
        
        if mega_df.empty:
            st.info("해당 섹터에 매핑된 테마 데이터가 없습니다.")
        else:
            # 3열(Column) 그리드로 카드 배치
            cols_per_row = 3
            rows_data = [mega_df.iloc[i:i + cols_per_row] for i in range(0, len(mega_df), cols_per_row)]
            
            for row_chunks in rows_data:
                grid_cols = st.columns(cols_per_row)
                for idx, (_, theme_row) in enumerate(row_chunks.iterrows()):
                    with grid_cols[idx]:
                        tid = theme_row["theme_id"]
                        name = theme_row["name_ko"]
                        ret_5d = theme_row["ret_5d"]
                        rvol = theme_row["med_rvol"]
                        q = theme_row["quality"]
                        v_icon = theme_row["velocity_icon"]
                        
                        # 5일 수익률에 따른 동적 배경색 설정 (히트맵 맵퍼)
                        if ret_5d >= 6.0:
                            bg_color = "linear-gradient(135deg, #022010, #04381c)"
                            border_color = "#00d97e"
                            text_color = "#00d97e"
                        elif ret_5d >= 1.5:
                            bg_color = "linear-gradient(135deg, #071f14, #0b301f)"
                            border_color = "#00d97e88"
                            text_color = "#85e8b4"
                        elif ret_5d <= -6.0:
                            bg_color = "linear-gradient(135deg, #28040a, #400711)"
                            border_color = "#ff3b5c"
                            text_color = "#ff3b5c"
                        elif ret_5d <= -1.5:
                            bg_color = "linear-gradient(135deg, #20070c, #300c14)"
                            border_color = "#ff3b5c88"
                            text_color = "#ffa6b4"
                        else:
                            bg_color = "linear-gradient(135deg, #0b1524, #122036)"
                            border_color = "#1e3a5f"
                            text_color = "#c9d1d9"
                            
                        # 카드 디자인
                        card_html = f"""
                        <div style="background:{bg_color};border:1px solid {border_color};border-radius:10px;
                                    padding:12px 14px;margin-bottom:8px;position:relative;">
                          <div style="font-size:11px;color:#7aa3cc;font-weight:600;">{theme_row['category']}</div>
                          <div style="font-size:14px;font-weight:800;color:#e6f3ff;margin-top:2px;
                                      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                            {name}
                          </div>
                          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:10px;">
                            <span style="color:{text_color};font-weight:800;font-size:16px;">{ret_5d:+.1f}%</span>
                            <span class="badge b-gray" style="margin:0;">Q:{q}점</span>
                          </div>
                          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px;font-size:11px;color:#7aa3cc;">
                            <span>RVOL: <b>{rvol:.1f}x</b></span>
                            <span>{v_icon}</span>
                          </div>
                        </div>
                        """
                        st.markdown(card_html, unsafe_allow_html=True)
                        
                        # 카드 바로 아래에 클릭해서 우측 분석을 로딩하는 깔끔한 버튼 배치
                        if st.button("👉 퀀트 상세분석", key=f"heatmap_btn_{tid}", use_container_width=True):
                            st.session_state.selected_theme_tab2 = tid
                            st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

        # 2. Interactive Bar Chart with Dynamic Height & Range Control
        plot_df = themes_df.copy()
        if not plot_df.empty:
            # 3가지 보기 옵션 제공 (가시성 및 클릭성 향상)
            chart_view_opt = st.radio(
                "📊 차트 표시 범위 설정 (클릭 시 높이가 동적 확장되어 클릭이 매우 쾌적해집니다)",
                ["주도 테마 TOP 15", "주도 테마 TOP 30", "전체 테마"],
                horizontal=True,
                key="bar_chart_view_option"
            )
            
            if chart_view_opt == "주도 테마 TOP 15":
                plot_df_sorted = plot_df.sort_values("ret_5d", ascending=True).tail(15)
            elif chart_view_opt == "주도 테마 TOP 30":
                plot_df_sorted = plot_df.sort_values("ret_5d", ascending=True).tail(30)
            else:
                plot_df_sorted = plot_df.sort_values("ret_5d", ascending=True)
            
            # 테마 개수에 따라 높이를 동적으로 계산 (1개당 35px 할당하여 두꺼운 클릭 면적 확보)
            num_items = len(plot_df_sorted)
            chart_height = max(350, num_items * 35 + 80)
            
            chart_title = f"실시간 테마별 5일 수익률 ({chart_view_opt}) (바 클릭 시 상세 분석 즉각 반영 🎯)"
            
            fig = px.bar(
                plot_df_sorted,
                x="ret_5d",
                y="name_ko",
                color="ret_5d",
                color_continuous_scale=["#ff3b5c", "#0f1a2e", "#00d97e"],
                color_continuous_midpoint=0,
                orientation="h",
                custom_data=["theme_id", "med_rvol", "quality"],
                hover_data={"ret_5d": ":+.1f%", "med_rvol": ":.2f}x", "quality": ":.0f"},
                title=chart_title,
                labels={"ret_5d": "5일 수익률 (%)", "name_ko": "테마명"}
            )
            fig.update_layout(
                paper_bgcolor="#080e18", plot_bgcolor="#0d1625",
                font={"color": "#c9d1d9", "family": "Inter"},
                margin=dict(l=10, r=10, t=50, b=10), height=chart_height,
                xaxis=dict(gridcolor="#1a2840", ticksuffix="%"),
                yaxis=dict(gridcolor="#1a2840", tickfont=dict(size=12, color="#e6f3ff")),
                coloraxis_colorbar=dict(title="5D%", tickfont=dict(color="#7aa3cc")),
                clickmode="event+select",
                bargap=0.35 # 바 간격을 넉넉히 확보하여 오클릭 방지
            )
            fig.update_traces(
                marker_line_width=1, marker_line_color="#1a2840",
                hovertemplate="<b>%{y}</b><br>5일 수익률: %{x:+.1f}%<br>상대 거래량(RVOL): %{customdata[1]:.2f}x<br>신호 점수: %{customdata[2]}점<extra></extra>"
            )
            
            # Capture selection event
            event = st.plotly_chart(fig, use_container_width=True, key="theme_bar_chart", on_select="rerun")
            
            # Safe extraction of points
            points = []
            if event:
                if hasattr(event, "selection") and event.selection and "points" in event.selection:
                    points = event.selection["points"]
                elif isinstance(event, dict) and "selection" in event and "points" in event["selection"]:
                    points = event["selection"]["points"]
                    
            if points:
                pt = points[0]
                if "customdata" in pt and pt["customdata"]:
                    clicked_tid = pt["customdata"][0]
                    if st.session_state.selected_theme_tab2 != clicked_tid:
                        st.session_state.selected_theme_tab2 = clicked_tid
                        st.rerun()

        # 3. Sortable table list with click buttons
        st.markdown("### 📋 테마 선택 리스트")
        sig_emoji = {"TRUE_SIGNAL":"🟢","WATCH":"⚠️","DEAD_CAT":"💀","PUMP":"🔴","OVERHEATED":"🌡️","NOISE":"⚫"}
        sig_label = {"TRUE_SIGNAL":"진짜신호","WATCH":"관찰중","DEAD_CAT":"데드캣","PUMP":"투기펌핑","OVERHEATED":"과열","NOISE":"신호없음"}

        for i, row in themes_df.iterrows():
            q = row["quality"]
            if q >= 65:   bar_color = "#00d97e"
            elif q >= 40: bar_color = "#f0b429"
            else:          bar_color = "#3a5070"

            ret_c5 = "#00d97e" if row["ret_5d"] >= 0 else "#ff3b5c"
            ret_c1 = "#00d97e" if row["ret_1d"] >= 0 else "#ff3b5c"

            col0, col1, col2, col3, col4, col5, col6 = st.columns([3,1.2,1,1,1.2,1.2,1])
            with col0:
                clicked = st.button(
                    f"{sig_emoji.get(row['signal_type'],'⚫')} {row['name_ko']} {row['velocity_icon']}",
                    key=f"board_btn_{i}",
                    use_container_width=True,
                )
                if clicked:
                    st.session_state.selected_theme_tab2 = row["theme_id"]
                    st.rerun()
            with col1:
                st.markdown(
                    f'<div style="margin-top:8px;"><div class="qbar-bg"><div class="qbar" style="width:{q}%;background:{bar_color};"></div></div>'
                    f'<span style="color:{bar_color};font-weight:700;font-size:13px;">{q}점</span></div>',
                    unsafe_allow_html=True
                )
            with col2:
                st.markdown(f'<div style="margin-top:8px;color:#f0b429;font-weight:600;">{row["med_rvol"]:.2f}x</div>', unsafe_allow_html=True)
            with col3:
                st.markdown(f'<div style="margin-top:8px;color:{ret_c1};font-weight:600;">{row["ret_1d"]:+.1f}%</div>', unsafe_allow_html=True)
            with col4:
                st.markdown(f'<div style="margin-top:8px;color:{ret_c5};font-weight:700;font-size:15px;">{row["ret_5d"]:+.1f}%</div>', unsafe_allow_html=True)
            with col5:
                st.markdown(f'<div style="margin-top:8px;color:#7aa3cc;">{row["breadth_1d"]:.0f}%</div>', unsafe_allow_html=True)
            with col6:
                st.markdown(f'<div style="margin-top:8px;color:#5a7a9a;">{row["stock_count"]}</div>', unsafe_allow_html=True)

    with col_right:
        st.markdown("### 🔍 퀀트 상세 분석 & 원픽 가이드")
        if st.session_state.selected_theme_tab2:
            tid = st.session_state.selected_theme_tab2
            cfg = themes_config.get(tid, {})
            theme_row = themes_df[themes_df["theme_id"] == tid]
            
            # Close button inside detail panel
            if st.button("✕ 상세분석 닫기", key="close_detail_tab2", use_container_width=True):
                st.session_state.selected_theme_tab2 = None
                st.rerun()
                
            _render_theme_detail(tid, theme_row, cfg, tab_name="tab2")
        else:
            st.markdown("""
            <div style="background:#0a1520;border:1px solid #1a3a5c;border-radius:12px;padding:36px 30px;text-align:center;margin-top:20px;">
              <div style="font-size:54px;margin-bottom:16px;">👈</div>
              <div style="color:#7ab8f5;font-weight:700;font-size:18px;margin-bottom:8px;">실시간 퀀트 분석 대기 중</div>
              <div style="color:#a0c4e8;font-size:13px;line-height:1.6;">
                왼쪽 화면에서 <b>[히트맵 타일]</b>, <b>[바 차트 막대]</b> 또는 <b>[테마 선택 리스트의 버튼]</b>을 클릭해 주십시오.<br>
                해당 테마의 5-Factor 점수 분석과 퀀트 추천 주도주/눌림목 원픽 정보가 스크롤 없이 이곳에 즉시 출력됩니다.
              </div>
            </div>
            """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════
# TAB 3: 상세 탐색기
# ════════════════════════════════════════════════════════════════════════
with tab_explorer:
    st.markdown("## 🔍 테마 상세 탐색기")

    cat_options = ["전체"] + list(THEME_CATEGORIES.keys())
    sel_cat = st.selectbox("카테고리", cat_options, key="explorer_cat")

    if sel_cat == "전체":
        cat_df = themes_df
    else:
        cat_theme_ids = set(THEME_CATEGORIES.get(sel_cat, []))
        cat_df = themes_df[themes_df["theme_id"].isin(cat_theme_ids)]

    if cat_df.empty:
        st.info("해당 카테고리에 데이터가 없습니다.")
    else:
        theme_names = cat_df["name_ko"].tolist()
        theme_ids   = cat_df["theme_id"].tolist()

        # Pre-select from session state if set
        default_idx = 0
        if st.session_state.selected_theme_tab3 in theme_ids:
            default_idx = theme_ids.index(st.session_state.selected_theme_tab3)

        sel_idx = st.selectbox(
            "테마 선택",
            range(len(theme_names)),
            format_func=lambda i: f"{theme_names[i]}",
            index=default_idx,
            key="explorer_theme_select"
        )

        tid = theme_ids[sel_idx]
        cfg = themes_config.get(tid, {})
        theme_row = cat_df[cat_df["theme_id"] == tid]
        st.session_state.selected_theme_tab3 = tid

        _render_theme_detail(tid, theme_row, cfg, tab_name="tab3")


    st.markdown("</div>", unsafe_allow_html=True)

