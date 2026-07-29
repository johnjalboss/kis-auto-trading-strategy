"""
fix_misclassifications.py - 검증 후 발견된 거짓분류 전부 수정
"""
import sqlite3
import json
import datetime

DB_PATH = "us_stocks_data.db"
THEME_DB_JSON = "theme_db.json"

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
        print(f"  REMOVED {theme_id} from {ticker}")

def add_theme(ticker, theme_id):
    cur.execute("SELECT COUNT(*) FROM stock_metadata WHERE ticker = ?", (ticker,))
    if cur.fetchone()[0] == 0:
        print(f"  SKIP {ticker} - not in DB")
        return
    themes = get_themes(ticker)
    if theme_id not in themes:
        themes.add(theme_id)
        set_themes(ticker, themes)
        print(f"  ADDED {theme_id} to {ticker}")

fixes = 0

print("=" * 60)
print("거짓분류 수정 시작")
print("=" * 60)

# ─── hyperscale_cloud 에서 잘못된 것들 제거 ─────────────────────
print("\n[hyperscale_cloud] 거짓분류 제거:")
# IonQ는 양자컴퓨터 (클라우드 아님)
remove_theme("IONQ", "hyperscale_cloud")
# Intuitive Machines는 우주 회사 (클라우드 아님)
remove_theme("LUNR", "hyperscale_cloud")
# Rumble은 소셜미디어/비디오 플랫폼 (클라우드 플랫폼 아님)
remove_theme("RUM", "hyperscale_cloud")
# TD SYNNEX는 IT유통사 (클라우드 공급자 아님)
remove_theme("SNX", "hyperscale_cloud")
# Fastly는 CDN/엣지 네트워크 (하이퍼스케일 아님)
remove_theme("FSLY", "hyperscale_cloud")
# CSCO는 네트워크 장비 (클라우드 플랫폼 공급자 아님)
remove_theme("CSCO", "hyperscale_cloud")

# ─── quantum_computing 에서 잘못된 것들 제거 ─────────────────────
print("\n[quantum_computing] 거짓분류 제거:")
# WDC는 저장장치 회사 (양자컴퓨터 아님)
remove_theme("WDC", "quantum_computing")
# Booz Allen Hamilton은 컨설팅 회사 (양자컴퓨터 제조 아님)
remove_theme("BAH", "quantum_computing")
# SkyWater Technology는 반도체 파운드리 (양자컴퓨터 아님)
remove_theme("SKYT", "quantum_computing")
# Aeluma는 광전자소자 (양자컴퓨터 아님)
remove_theme("ALMU", "quantum_computing")

# ─── power_generation_equipment 에서 잘못된 것들 제거 ──────────
print("\n[power_generation_equipment] 거짓분류 제거:")
# GE Aerospace는 항공기 엔진 회사 (발전 터빈 아님, 분사한 자회사 GEV가 발전쪽)
remove_theme("GE", "power_generation_equipment")
# WEC Energy Group는 전력유틸리티 (발전장비 제조 아님)
remove_theme("WEC", "power_generation_equipment")
# Kirby Corporation는 선박운송 (발전장비 아님)
remove_theme("KEX", "power_generation_equipment")
# AEP는 전력유틸리티 (제조사 아님)
remove_theme("AEP", "power_generation_equipment")

# ─── power_grid_transformers 에서 잘못된 것들 제거 ──────────────
print("\n[power_grid_transformers] 거짓분류 제거:")
# United Rentals은 장비렌탈 (송배전 장비 제조 아님)
remove_theme("URI", "power_grid_transformers")
# AEP는 유틸리티 운영사 (그리드 장비 제조 아님)
remove_theme("AEP", "power_grid_transformers")
# Ameren는 유틸리티 운영사 (장비 제조 아님)
remove_theme("AEE", "power_grid_transformers")
# Orion Group은 건설 시공사 (장비 제조 아님)
remove_theme("ORN", "power_grid_transformers")
# Resideo는 가정용 온도조절기/보안 (송배전 아님)
remove_theme("REZI", "power_grid_transformers")

# ─── bitcoin_proxies 에서 잘못된 것들 제거 ───────────────────────
print("\n[bitcoin_proxies] 거짓분류 제거:")
# DJT (Trump Media)는 소셜미디어/스트리밍 (비트코인 보유기업 아님)
remove_theme("DJT", "bitcoin_proxies")

# ─── datacenter_reits 에서 잘못된 것들 제거 ──────────────────────
print("\n[datacenter_reits] 거짓분류 제거:")
# IRON - 이건 ticker가 혈액질환 바이오텍 Disc Medicine으로 잘못 매핑됨
# 실제 데이터센터 리츠 Iron Mountain은 IRM
remove_theme("IRON", "datacenter_reits")
add_theme("IRM", "datacenter_reits")  # Iron Mountain이 실제 데이터센터 리츠

# ─── uav_defense_drones 에서 잘못된 것들 제거 ──────────────────
print("\n[uav_defense_drones] 거짓분류 제거:")
# JOBY Aviation은 eVTOL 항공택시 (군용 드론 아님)
remove_theme("JOBY", "uav_defense_drones")

# ─── dram_memory 에서 잘못된 것들 제거 ─────────────────────────
print("\n[dram_memory] 거짓분류 제거:")
# Penguin Solutions는 엔터프라이즈 솔루션 (DRAM 제조 아님)
remove_theme("PENG", "dram_memory")
# Veeco는 반도체 장비 (DRAM 제조 아님)  
remove_theme("VECO", "dram_memory")

# ─── hydrogen_fuel_cells 에서 잘못된 것들 제거 ─────────────────
print("\n[hydrogen_fuel_cells] 거짓분류 제거:")
# Dana Incorporated는 자동차 파워트레인 (수소연료전지 기업 아님)
remove_theme("DAN", "hydrogen_fuel_cells")

# ─── nand_memory 에서 잘못된 것들 제거 ─────────────────────────
print("\n[nand_memory] 거짓분류 제거:")
# AMKR (Amkor)는 반도체 패키징/테스트 서비스 (NAND 설계/제조 아님)
remove_theme("AMKR", "nand_memory")
# FormFactor는 probe card 제조 (NAND 칩 제조 아님)
remove_theme("FORM", "nand_memory")

# ─── custom_ai_chips 에서 잘못된 것들 제거 ──────────────────────
print("\n[custom_ai_chips] 거짓분류 제거:")
# Allegro MicroSystems는 자동차/산업용 센서 IC (AI chip 전문 아님)
remove_theme("ALGM", "custom_ai_chips")
# QCOM도 주로 모바일 통신칩 (AI chip 전문 아님 - 하지만 AI On-Device 있으므로 유지)

# ─── generative_ai_platforms 에서 잘못된 것들 제거 ──────────────
print("\n[generative_ai_platforms] 거짓분류 제거:")
# Cerebras는 AI 칩 제조사 (LLM 플랫폼 아님 -> custom_ai_chips가 맞음)
remove_theme("CBRS", "generative_ai_platforms")
add_theme("CBRS", "custom_ai_chips")
# BigBear.ai는 정부/국방 AI 소프트웨어 (LLM 플랫폼 아님 -> ai_software_enterprise가 맞음)
remove_theme("BBAI", "generative_ai_platforms")

# ─── smr_nuclear 에서 잘못된 것들 제거 ─────────────────────────
print("\n[smr_nuclear] 거짓분류 제거:")
# Eagle Nuclear Energy Corp (NUCL)은 광산 탐사회사 (SMR 기술 아님)
remove_theme("NUCL", "smr_nuclear")
# Fluor는 엔지니어링/건설 (SMR 기술 개발사 아님, 건설 도급사임)
remove_theme("FLR", "smr_nuclear")

# ─── commercial_space_launch 에서 맞지 않는 것들 제거 ─────────
print("\n[commercial_space_launch] 거짓분류 제거:")
# Virgin Galactic (SPCE)는 우주관광 (로켓 발사 서비스 아님)
remove_theme("SPCE", "commercial_space_launch")
add_theme("SPCE", "satellite_communication")  # 우주 관련으로 이동
# LMT (Lockheed Martin)은 방산 prime (발사체도 있지만 주업이 아님)
# defense_primes로 충분

# ─── grid_scale_batteries 에서 잘못된 것들 제거 ────────────────
print("\n[grid_scale_batteries] 거짓분류 제거:")
# Generac는 발전기 제조 (BESS/ESS 아님)
remove_theme("GNRC", "grid_scale_batteries")

# ─── solar_panels 에서 잘못된 것들 제거 ────────────────────────
print("\n[solar_panels] 거짓분류 제거:")
# Shoals Technologies는 태양광 EBOS 부품 (패널 제조 아님 - 별도 부품 공급)
# 사실 태양광 BOS 공급업체로 맞기는 함, 그냥 유지
# Array Technologies는 태양광 트래커 (패널 제조 아님)
# 이것도 태양광 관련이라 유지

# ─── 누락된 중요 종목 추가 ──────────────────────────────────────
print("\n[중요 누락 종목 추가]:")

# ASML은 DB에 있을텐데 lithography_equipment에 없었음
add_theme("ASML", "lithography_equipment")

# 우라늄 관련 추가
add_theme("UEC", "uranium_mining")
add_theme("UUUU", "uranium_mining")
add_theme("NXE", "uranium_mining")

# 반도체 웨이퍼/소재 (CCMP - CMC Materials)
add_theme("CCMP", "semiconductor_wafers")
add_theme("ENTG", "semiconductor_wafers")  # 반도체 특수 화학

# Amkor는 패키징 (wafer level packaging)
add_theme("AMKR", "semiconductor_wafers")
# FormFactor는 probe card
add_theme("FORM", "etching_deposition_equipment")

# eVTOL - JOBY는 eVTOL에 맞음
add_theme("JOBY", "evtol_flying_cars")

# gpu_cloud에 추가 (AI 전용 데이터센터 운영사)
add_theme("HUT", "gpu_cloud_infrastructure")  # Hut8 - AI computing + bitcoin mining

# Generac는 백업 발전기 - 데이터센터 전력으로 분류
add_theme("GNRC", "power_grid_transformers")  

# PENG (Penguin Solutions)는 HPC 솔루션 -> server_manufacturers로
add_theme("PENG", "server_manufacturers")

# VECO (Veeco)는 반도체 장비에 맞음 (MBE, ALD 등)
add_theme("VECO", "etching_deposition_equipment")

conn.commit()

# ─── 최종 검증 출력 ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("수정 완료 - 주요 테마 최종 종목 수 확인")
print("=" * 60)

check_themes = [
    "nand_memory", "dram_memory", "server_manufacturers",
    "gpu_cloud_infrastructure", "hyperscale_cloud", "quantum_computing",
    "power_generation_equipment", "power_grid_transformers",
    "bitcoin_proxies", "datacenter_reits", "uav_defense_drones",
    "hydrogen_fuel_cells", "lithography_equipment", "uranium_mining",
    "custom_ai_chips", "smr_nuclear", "optical_interconnects"
]

with open(THEME_DB_JSON, "r", encoding="utf-8") as f:
    themes_config = json.load(f)["themes"]

for tid in check_themes:
    cur.execute("SELECT ticker, name FROM stock_metadata WHERE theme_tags LIKE ?", (f"%{tid}%",))
    rows = cur.fetchall()
    name_ko = themes_config.get(tid, {}).get("name_ko", tid)
    print(f"\n[{tid}] {name_ko} - {len(rows)}개")
    for ticker, name in rows:
        print(f"  {ticker:8s} {(name or '')[:50]}")

conn.close()
print("\n모든 수정 완료!")
