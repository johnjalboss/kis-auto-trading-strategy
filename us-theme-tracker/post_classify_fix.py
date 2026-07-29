"""
post_classify_fix.py
키워드 매칭의 한계로 발생한 거짓분류를 한 번에 수정
"""
import sqlite3
import json
import datetime

DB_PATH = "us_stocks_data.db"
THEME_DB_JSON = "theme_db.json"

with open(THEME_DB_JSON, "r", encoding="utf-8") as f:
    themes_config = json.load(f)["themes"]

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

def get_themes(ticker):
    cur.execute("SELECT theme_tags FROM stock_metadata WHERE ticker = ?", (ticker,))
    row = cur.fetchone()
    return set(t.strip() for t in (row[0] or "").split(",") if t.strip()) if row else set()

def set_themes(ticker, themes_set):
    cur.execute(
        "UPDATE stock_metadata SET theme_tags = ?, last_updated = ? WHERE ticker = ?",
        (",".join(sorted(themes_set)), datetime.datetime.now().isoformat(), ticker)
    )

def remove_theme(ticker, theme_id):
    themes = get_themes(ticker)
    if theme_id in themes:
        themes.discard(theme_id)
        set_themes(ticker, themes)
        return True
    return False

def add_theme(ticker, theme_id):
    cur.execute("SELECT COUNT(*) FROM stock_metadata WHERE ticker = ?", (ticker,))
    if cur.fetchone()[0] == 0:
        return False
    themes = get_themes(ticker)
    themes.add(theme_id)
    set_themes(ticker, themes)
    return True

fixes = []

# ════════════════════════════════════════════════════════════════════════
# nand_memory 수정: PENG, OSS는 제거
# ════════════════════════════════════════════════════════════════════════
for t in ["PENG", "OSS"]:
    if remove_theme(t, "nand_memory"):
        fixes.append(f"REMOVE nand_memory from {t}")

# ════════════════════════════════════════════════════════════════════════
# server_manufacturers: SMCIP는 SMCI의 우선주 - 보통주만 유지
# ════════════════════════════════════════════════════════════════════════
# SMCIP 자체는 주식이 아닌 우선주이므로 server 분류는 유지 (OK)

# ════════════════════════════════════════════════════════════════════════
# gpu_cloud_infrastructure 수정
# GOOGL/GOOG - 하이퍼스케일 클라우드가 맞음, gpu_cloud 제거
# NVDA - chip 제조사이지 클라우드 임대 아님
# ALAB - Astera Labs는 연결 반도체 (PCIe/UCIe) 임
# GDYN - Grid Dynamics는 IT 컨설팅
# SHAZ - SharonAI Holdings는 소규모 AI 회사
# ════════════════════════════════════════════════════════════════════════
for t in ["GOOGL", "GOOG", "NVDA", "ALAB", "PENG", "SHAZ", "GDYN"]:
    if remove_theme(t, "gpu_cloud_infrastructure"):
        fixes.append(f"REMOVE gpu_cloud_infrastructure from {t}")

# ALAB은 AI 네트워크 인터커넥트로 분류
add_theme("ALAB", "optical_interconnects")
fixes.append("ADD optical_interconnects to ALAB")

# APLD (Applied Digital) - AI 데이터센터 인프라 임대, 이건 gpu_cloud OK
# HUT는 비트코인 채굴+AI compute, gpu_cloud 유지

# ════════════════════════════════════════════════════════════════════════
# power_generation_equipment 수정 - 너무 많은 거짓분류
# 정확한 기업: 발전기, 가스터빈, 풍력터빈 제조사만
# CAT - 디젤 발전기 포함하지만 건설장비가 주업 → 제거
# HWM - 항공 엔진 부품, 발전 터빈 부품 포함 → 유지 (산업용 터빈)
# HEI (Heico) - 항공기 부품 → 제거
# CW (Curtiss-Wright) - 방산/산업 → 제거  
# WWD (Woodward) - 연료 제어 시스템 (터빈용) → 유지
# NI (NiSource) - 유틸리티 회사 → 제거
# LNT (Alliant Energy) - 유틸리티 → 제거
# TSCO (Tractor Supply) - 농업 소매 → 제거
# LECO (Lincoln Electric) - 용접 장비 → 제거
# WLK (Westlake) - 화학 → 제거
# AMSC - 전력 전자/초전도 → 유지 (그리드 파워)
# HNRG - 석탄 에너지 → 제거
# TWI (Titan International) - 산업용 타이어 → 제거
# ════════════════════════════════════════════════════════════════════════
for t in ["CAT", "HEI", "CW", "NI", "LNT", "TSCO", "GNRC", "LECO", "WLK", "HNRG", "TWI"]:
    if remove_theme(t, "power_generation_equipment"):
        fixes.append(f"REMOVE power_generation_equipment from {t}")

# AMSC는 power_grid_transformers가 더 맞음
add_theme("AMSC", "power_grid_transformers")
fixes.append("ADD power_grid_transformers to AMSC")
remove_theme("AMSC", "power_generation_equipment")

# GNRC는 발전기이지만 ESS도 함
add_theme("GNRC", "grid_scale_batteries")

# ════════════════════════════════════════════════════════════════════════
# smr_nuclear 수정
# NNE (Nano Nuclear Energy) - SMR 개발사, OK
# ASPI (ASP Isotopes) - 동위원소 농축, 핵연료 연관이지만 너무 소규모
# PACB (Pacific Biosciences) - 유전체 시퀀서 회사! 완전히 거짓분류
# ════════════════════════════════════════════════════════════════════════
remove_theme("PACB", "smr_nuclear")
fixes.append("REMOVE smr_nuclear from PACB")
# PACB는 genomics_sequencing
add_theme("PACB", "genomics_sequencing")
fixes.append("ADD genomics_sequencing to PACB")

# ASPI - 우라늄 농축 연관이므로 uranium_mining이 더 맞음
remove_theme("ASPI", "smr_nuclear")
add_theme("ASPI", "uranium_mining")
fixes.append("MOVE ASPI: smr_nuclear -> uranium_mining")

# ════════════════════════════════════════════════════════════════════════
# quantum_computing 수정
# FORM (FormFactor) - probe card 장비, quantum 아님
# ════════════════════════════════════════════════════════════════════════
remove_theme("FORM", "quantum_computing")
fixes.append("REMOVE quantum_computing from FORM")
add_theme("FORM", "semiconductor_test_equipment")
fixes.append("ADD semiconductor_test_equipment to FORM")

# ════════════════════════════════════════════════════════════════════════
# custom_ai_chips 수정
# CRWV - 클라우드 인프라 (칩 설계 아님)
# SMCI, SMCIP - 서버 제조 (칩 설계 아님)
# DOCN (DigitalOcean) - 클라우드 플랫폼 (칩 아님)
# APLD (Applied Digital) - 데이터센터 인프라 (칩 아님)
# PENG - HPC 서버 솔루션 (칩 아님)
# BRUN, BRUNW - 소규모 AI 회사 (칩 설계 아님)
# SHAZ - 소규모 AI (칩 아님)
# ════════════════════════════════════════════════════════════════════════
false_ai_chips = ["CRWV", "SMCI", "SMCIP", "DOCN", "APLD", "PENG", "BRUN", "BRUNW", "SHAZ"]
for t in false_ai_chips:
    if remove_theme(t, "custom_ai_chips"):
        fixes.append(f"REMOVE custom_ai_chips from {t}")

# CRWV → gpu_cloud_infrastructure
add_theme("CRWV", "gpu_cloud_infrastructure")
# APLD → gpu_cloud_infrastructure (AI datacenter host)
add_theme("APLD", "gpu_cloud_infrastructure")
fixes.append("ADD gpu_cloud_infrastructure to APLD")
# DOCN → hyperscale_cloud (developer cloud)
add_theme("DOCN", "hyperscale_cloud")
fixes.append("ADD hyperscale_cloud to DOCN")

# ════════════════════════════════════════════════════════════════════════
# bitcoin_proxies 수정
# DJT (Trump Media) - 소셜미디어 + Truth Social, 비트코인 보유 아님
# ════════════════════════════════════════════════════════════════════════
remove_theme("DJT", "bitcoin_proxies")
fixes.append("REMOVE bitcoin_proxies from DJT")
add_theme("DJT", "social_media_platforms")  # Truth Social
fixes.append("ADD social_media_platforms to DJT")

# ════════════════════════════════════════════════════════════════════════
# uav_defense_drones 수정 - 대규모 거짓분류
# MRK (Merck) - 제약회사, "uav"가 포함된 문자열 있는지?
# CL (Colgate) - 소비재
# TTMI (TTM Technologies) - PCB 제조
# VSAT (ViaSat) - 위성통신
# ZWS (Zurn Elkay) - 수도/배관
# LGND (Ligand Pharma) - 바이오
# WTTR (Select Water Solutions) - 수자원
# CTKB (Cytek Biosciences) - 유세포분석기
# PDYN (Palladyne AI) - AI 소프트웨어
# ════════════════════════════════════════════════════════════════════════
false_uav = ["MRK", "CL", "TTMI", "VSAT", "ZWS", "LGND", "WTTR", "CTKB", "PDYN", "MRCY"]
for t in false_uav:
    if remove_theme(t, "uav_defense_drones"):
        fixes.append(f"REMOVE uav_defense_drones from {t}")

# TTMI는 PCB 제조 (반도체 기판)
add_theme("TTMI", "semiconductor_wafers")
fixes.append("ADD semiconductor_wafers to TTMI")
# MRCY는 방산 전자 시스템 (defense OK)
add_theme("MRCY", "defense_primes")
# VSAT는 위성통신 OK
add_theme("VSAT", "satellite_communication")

# ════════════════════════════════════════════════════════════════════════
# lithography_equipment 수정 - 21개는 너무 많음
# 진짜 EUV/DUV 장비: ASML, Photronics, Cohu (포토마스크)
# 나머지는 "lithography" 키워드 과매칭 가능성
# ════════════════════════════════════════════════════════════════════════
cur.execute("SELECT ticker, name FROM stock_metadata WHERE theme_tags LIKE '%lithography_equipment%'")
litho_stocks = cur.fetchall()
print("lithography_equipment 전체 확인:")
legit_litho = {"ASML", "PLAB", "CAMT", "ONTO", "TER"}  # 정말 맞는 것들
for ticker, name in litho_stocks:
    if ticker not in legit_litho:
        remove_theme(ticker, "lithography_equipment")
        fixes.append(f"REMOVE lithography_equipment from {ticker}")
        print(f"  REMOVED from {ticker} ({name})")

# ════════════════════════════════════════════════════════════════════════
# carbon_capture 수정 - 21개는 너무 많음
# 진짜 CCS: Climeworks, Carbon Engineering 등
# 많은 에너지 회사가 "탄소 감소" 언급으로 과매칭됨
# ════════════════════════════════════════════════════════════════════════
cur.execute("SELECT ticker, name FROM stock_metadata WHERE theme_tags LIKE '%carbon_capture%'")
carbon_stocks = cur.fetchall()
# 진짜 CCS 전문 기업
legit_carbon = {"HLTH", "CTRA", "CLWF", "NET", "XPRT", "AEAC"}
print("\ncarbon_capture 확인:")
for ticker, name in carbon_stocks:
    if ticker not in legit_carbon:
        # 요약에서 "carbon capture" 또는 "direct air capture"가 명시적으로 있는지 확인
        cur.execute("SELECT summary FROM stock_metadata WHERE ticker = ?", (ticker,))
        summary = (cur.fetchone() or [""])[0] or ""
        if "direct air capture" not in summary.lower() and "carbon capture" not in summary.lower() and "sequestration" not in summary.lower():
            remove_theme(ticker, "carbon_capture")
            fixes.append(f"REMOVE carbon_capture from {ticker}")
            print(f"  REMOVED from {ticker} ({name})")

# ════════════════════════════════════════════════════════════════════════
# nuclear_utilities 수정 - 21개, 전력 유틸리티만 포함되어야 함
# 하지만 원자력 발전 운영사만: CEG, VST, EXC, PEG, D, SO 등
# ════════════════════════════════════════════════════════════════════════
cur.execute("SELECT ticker, name FROM stock_metadata WHERE theme_tags LIKE '%nuclear_utilities%'")
nuclear_stocks = cur.fetchall()
legit_nuclear = {"CEG", "VST", "EXC", "PEG", "D", "SO", "DUK", "AEE", "PPL", "ETR", "EIX"}
print("\nnuclear_utilities 확인:")
for ticker, name in nuclear_stocks:
    if ticker not in legit_nuclear:
        cur.execute("SELECT summary FROM stock_metadata WHERE ticker = ?", (ticker,))
        summary = (cur.fetchone() or [""])[0] or ""
        if "nuclear" not in summary.lower():
            remove_theme(ticker, "nuclear_utilities")
            fixes.append(f"REMOVE nuclear_utilities from {ticker}")
            print(f"  REMOVED from {ticker}")

conn.commit()

# ════════════════════════════════════════════════════════════════════════
# 최종 핵심 테마 카운트 출력
# ════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print(f"총 수정 건수: {len(fixes)}")
print("=" * 60)

key_themes = [
    "nand_memory", "dram_memory", "server_manufacturers", "gpu_cloud_infrastructure",
    "custom_ai_chips", "quantum_computing", "power_generation_equipment",
    "smr_nuclear", "uav_defense_drones", "bitcoin_proxies", "lithography_equipment",
    "carbon_capture", "nuclear_utilities"
]

for tid in key_themes:
    cur.execute("SELECT ticker, name FROM stock_metadata WHERE theme_tags LIKE ?", (f"%{tid}%",))
    rows = cur.fetchall()
    name_ko = themes_config.get(tid, {}).get("name_ko", tid)
    print(f"\n[{tid}] {name_ko} - {len(rows)}개:")
    for ticker, name in rows:
        print(f"  {ticker:8s} {(name or '')[:50]}")

conn.close()
print("\n수정 완료!")
