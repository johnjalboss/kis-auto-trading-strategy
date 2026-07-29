"""
final_cleanup.py - 마지막 정밀 수정
"""
import sqlite3, json, datetime, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB_PATH = "us_stocks_data.db"
with open("theme_db.json", "r", encoding="utf-8") as f:
    themes_config = json.load(f)["themes"]

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

def get_themes(t):
    cur.execute("SELECT theme_tags FROM stock_metadata WHERE ticker=?", (t,))
    r = cur.fetchone()
    return set(x.strip() for x in (r[0] or "").split(",") if x.strip()) if r else set()

def set_themes(t, s):
    cur.execute("UPDATE stock_metadata SET theme_tags=?, last_updated=? WHERE ticker=?",
                (",".join(sorted(s)), datetime.datetime.now().isoformat(), t))

def rm(ticker, tid):
    s = get_themes(ticker)
    if tid in s:
        s.discard(tid)
        set_themes(ticker, s)
        print(f"  RM {tid} from {ticker}")

def add(ticker, tid):
    cur.execute("SELECT COUNT(*) FROM stock_metadata WHERE ticker=?", (ticker,))
    if cur.fetchone()[0] == 0: return
    s = get_themes(ticker)
    s.add(tid)
    set_themes(ticker, s)
    print(f"  ADD {tid} to {ticker}")

# ── dram_memory 수정 ──────────────────────────────────────────────────
# AMD는 HBM GPU 메모리 사용하지만 DRAM 제조사 아님
# TER (Teradyne)는 테스트 장비
# PENG는 HPC 솔루션 공급사
for t in ["AMD", "TER", "PENG"]:
    rm(t, "dram_memory")
# TER는 semiconductor_test_equipment
add("TER", "semiconductor_test_equipment")

# ── nuclear_utilities 정밀 수정 ───────────────────────────────────────
# CW (Curtiss-Wright) - 방산 회사, 원자력 서비스 부문 있지만 주업이 국방
rm("CW", "nuclear_utilities")
add("CW", "defense_primes")
# NPO (Enpro) - 산업 밀봉재, 원자력 아님
rm("NPO", "nuclear_utilities")
add("NPO", "industrial_automation")
# IMSR (Terrestrial Energy) - SMR 개발사, nuclear_utilities보다 smr_nuclear가 맞음
rm("IMSR", "nuclear_utilities")
add("IMSR", "smr_nuclear")
# NUCL (Eagle Nuclear Energy) - 광산 탐사, uranium_mining
rm("NUCL", "nuclear_utilities")
add("NUCL", "uranium_mining")
# NNE - SMR 개발사, smr_nuclear가 맞음
rm("NNE", "nuclear_utilities")  # 이미 smr_nuclear 있음
# LEU - 핵연료 농축, uranium_mining이 더 맞음
rm("LEU", "nuclear_utilities")  # uranium_mining 이미 있음

# ── carbon_capture 수정 ──────────────────────────────────────────────
# XOM, CVX - 대형 오일사, CCS 프로젝트 있지만 주업 아님
# ADM - 농업기업
# MTZ, FLR - 건설 도급 (CCS 건설 하지만 주업 아님)
for t in ["XOM", "CVX", "ADM", "MTZ", "FLR"]:
    rm(t, "carbon_capture")

# TALO (Talos Energy), NEXT (NextDecade) - E&P이지만 CCS 프로젝트 실제로 있음 → 유지
# FCEL - 수소연료전지, carbon_capture 아님
rm("FCEL", "carbon_capture")

# ── dram_memory에 빠진 것 추가 ────────────────────────────────────────
# HBM 관련: SK하이닉스는 미국 상장 안됨, Rambus(RMBS)는 메모리 인터페이스 OK

# ── custom_ai_chips 추가 ────────────────────────────────────────────
# KLAC는 반도체 공정 검사장비, etching/deposition에 이미 있음
add("KLAC", "etching_deposition_equipment")

# ── optical_interconnects 추가 ──────────────────────────────────────
# NEOPHOTONICS 계열, Lumentum OK
# II-VI → COHR (합병) 이미 있음
# POET Technologies
cur.execute("SELECT ticker FROM stock_metadata WHERE ticker='POET'")
if cur.fetchone():
    add("POET", "optical_interconnects")

# ── ai_networking_switches 추가 ────────────────────────────────────
# Broadcom도 AI networking 칩 (Tomahawk, Trident)
add("AVGO", "ai_networking_switches")
# Marvell도 ethernet switching
add("MRVL", "ai_networking_switches")

# ── hyperscale_cloud에서 잘못된 것 제거 ───────────────────────────
# DigitalOcean은 중소기업 클라우드 (하이퍼스케일 아님)
rm("DOCN", "hyperscale_cloud")
add("DOCN", "crm_enterprise_saas")  # SMB cloud platform

# ── power_grid_transformers 추가 ─────────────────────────────────
# Vertiv Holdings - 데이터센터 전력/냉각이 주업이지만 그리드 장비도 함
add("VRT", "power_grid_transformers")

# ── 마지막 전체 통계 ────────────────────────────────────────────────
conn.commit()

cur.execute("SELECT COUNT(*) FROM stock_metadata WHERE theme_tags != '' AND theme_tags IS NOT NULL")
classified = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM stock_metadata")
total = cur.fetchone()[0]
print(f"\n최종: {classified}/{total}개 분류 ({classified/total*100:.1f}%)")

# 전체 테마별 종목 수
cur.execute("SELECT ticker, theme_tags FROM stock_metadata WHERE theme_tags != ''")
all_tags = cur.fetchall()
counts = {}
for _, tags in all_tags:
    for t in tags.split(","):
        t = t.strip()
        if t: counts[t] = counts.get(t,0) + 1

print("\n=== 전체 테마 최종 현황 ===")
for tid, cnt in sorted(counts.items(), key=lambda x: -x[1]):
    name_ko = themes_config.get(tid,{}).get("name_ko", tid)
    print(f"  {cnt:4d}  {tid:40s} {name_ko}")

conn.close()
print("\n완료!")
