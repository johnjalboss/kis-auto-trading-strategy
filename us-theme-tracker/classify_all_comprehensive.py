"""
classify_all_comprehensive.py
================================================================================
3000+ 미국 상장주식 전체 정밀 분류 엔진 (v3.0)
- Pass 1: premapped_tickers (확정 종목)
- Pass 2: 요약(summary) 키워드 매칭 (strict 포지티브 + 네거티브 필터)
- Pass 3: 업종(industry) 기반 fallback 분류 (요약 없는 종목)
- Pass 4: 이름(name) 기반 분류 (최후 수단)
================================================================================
"""
import sqlite3
import json
import re
import sys
import io
import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB_PATH = "us_stocks_data.db"
THEME_DB_JSON = "theme_db.json"

# ─── Load theme config ─────────────────────────────────────────────────────
with open(THEME_DB_JSON, "r", encoding="utf-8") as f:
    themes_config = json.load(f)["themes"]

# ─── Industry → Theme mapping (Pass 3 fallback) ───────────────────────────
# Maps yfinance industry strings to theme IDs (ordered by specificity)
INDUSTRY_THEME_MAP = {
    # Semiconductors
    "Semiconductors": ["analog_mixed_signal"],
    "Semiconductor Equipment & Materials": ["etching_deposition_equipment"],

    # Software
    "Software - Application": ["crm_enterprise_saas"],
    "Software - Infrastructure": ["next_gen_cybersecurity"],
    "Information Technology Services": ["crm_enterprise_saas"],

    # Finance
    "Banks - Regional": ["regional_banks"],
    "Banks - Diversified": ["regional_banks"],
    "Insurance - Life": ["insurance"],
    "Insurance - Property & Casualty": ["insurance"],
    "Insurance - Specialty": ["insurance"],
    "Insurance - Diversified": ["insurance"],
    "Insurance - Reinsurance": ["insurance"],
    "Insurance Brokers": ["insurance"],
    "Asset Management": ["asset_management"],
    "Capital Markets": ["asset_management"],
    "Financial Data & Stock Exchanges": ["trading_brokerage"],
    "Credit Services": ["payments_fintech"],
    "Mortgage Finance": ["reits_real_estate"],

    # Real Estate
    "REIT - Residential": ["reits_real_estate"],
    "REIT - Industrial": ["reits_real_estate"],
    "REIT - Office": ["reits_real_estate"],
    "REIT - Retail": ["reits_real_estate"],
    "REIT - Healthcare Facilities": ["reits_real_estate"],
    "REIT - Specialty": ["reits_real_estate"],
    "REIT - Mortgage": ["reits_real_estate"],
    "REIT - Hotel & Motel": ["reits_real_estate"],
    "REIT - Diversified": ["reits_real_estate"],
    "Real Estate Services": ["reits_real_estate"],

    # Energy
    "Solar": ["solar_panels"],
    "Uranium": ["uranium_mining"],
    "Oil & Gas E&P": ["oil_gas_exploration"],
    "Oil & Gas Integrated": ["oil_gas_exploration"],
    "Oil & Gas Drilling": ["oil_gas_exploration"],
    "Oil & Gas Equipment & Services": ["oil_gas_exploration"],
    "Oil & Gas Refining & Marketing": ["oil_gas_exploration"],
    "Oil & Gas Midstream": ["pipeline_midstream"],
    "Utilities - Regulated Electric": ["nuclear_utilities"],
    "Utilities - Independent Power Producers": ["nuclear_utilities"],
    "Utilities - Renewable": ["wind_energy"],
    "Utilities - Regulated Gas": ["pipeline_midstream"],
    "Utilities - Regulated Water": ["water_infrastructure"],
    "Utilities - Diversified": ["nuclear_utilities"],

    # Healthcare
    "Biotechnology": ["pharmaceuticals_traditional"],
    "Drug Manufacturers - General": ["pharmaceuticals_traditional"],
    "Drug Manufacturers - Specialty & Generic": ["pharmaceuticals_traditional"],
    "Medical Devices": ["medical_devices_general"],
    "Medical Instruments & Supplies": ["medical_devices_general"],
    "Medical Care Facilities": ["telehealth"],
    "Health Information Services": ["telehealth"],
    "Healthcare Plans": ["insurance"],
    "Diagnostics & Research": ["diagnostics_lab_instruments"],
    "Medical Distribution": ["pharmaceuticals_traditional"],

    # Consumer
    "Internet Content & Information": ["social_media_platforms"],
    "Internet Retail": ["ecommerce_marketplace"],
    "Specialty Retail": ["retail_stores"],
    "Discount Stores": ["retail_stores"],
    "Department Stores": ["retail_stores"],
    "Grocery Stores": ["retail_stores"],
    "Apparel Retail": ["apparel_footwear"],
    "Apparel Manufacturing": ["apparel_footwear"],
    "Footwear & Accessories": ["apparel_footwear"],
    "Restaurants": ["restaurants_food"],
    "Travel Services": ["online_travel"],
    "Resorts & Casinos": ["sports_betting"],
    "Gambling": ["sports_betting"],
    "Electronic Gaming & Multimedia": ["online_gaming_esports"],
    "Entertainment": ["streaming_media_ott"],
    "Beverages - Non-Alcoholic": ["restaurants_food"],
    "Beverages - Brewers": ["restaurants_food"],
    "Packaged Foods": ["restaurants_food"],
    "Confectioners": ["restaurants_food"],
    "Food Distribution": ["air_freight_logistics"],
    "Farm Products": ["pharmaceuticals_traditional"],
    "Household & Personal Products": ["retail_stores"],
    "Luxury Goods": ["apparel_footwear"],
    "Personal Services": ["telehealth"],

    # Auto
    "Auto Manufacturers": ["auto_manufacturers"],
    "Auto Parts": ["auto_manufacturers"],
    "Auto & Truck Dealerships": ["auto_manufacturers"],

    # Aerospace
    "Aerospace & Defense": ["defense_primes"],
    "Airports & Air Services": ["air_freight_logistics"],

    # Industrial
    "Specialty Industrial Machinery": ["industrial_automation"],
    "Farm & Heavy Construction Machinery": ["industrial_automation"],
    "Electrical Equipment & Parts": ["power_grid_transformers"],
    "Metal Fabrication": ["steel_metals"],
    "Steel": ["steel_metals"],
    "Aluminum": ["steel_metals"],
    "Copper": ["copper_mining"],
    "Gold": ["steel_metals"],
    "Other Precious Metals & Mining": ["rare_earth_elements"],
    "Other Industrial Metals & Mining": ["steel_metals"],
    "Building Materials": ["construction_materials"],
    "Building Products & Equipment": ["construction_materials"],
    "Specialty Chemicals": ["specialty_chemicals"],
    "Chemicals": ["specialty_chemicals"],
    "Agricultural Inputs": ["specialty_chemicals"],
    "Engineering & Construction": ["industrial_automation"],
    "Integrated Freight & Logistics": ["air_freight_logistics"],
    "Trucking": ["air_freight_logistics"],
    "Railroads": ["air_freight_logistics"],
    "Marine Shipping": ["air_freight_logistics"],
    "Rental & Leasing Services": ["industrial_automation"],
    "Tools & Accessories": ["industrial_automation"],
    "Electronic Components": ["analog_mixed_signal"],
    "Computer Hardware": ["server_manufacturers"],
    "Communication Equipment": ["enterprise_networking"],
    "Scientific & Technical Instruments": ["diagnostics_lab_instruments"],
    "Packaging & Containers": ["specialty_chemicals"],
    "Industrial Distribution": ["air_freight_logistics"],
    "Waste Management": ["solid_waste_recycling"],
    "Pollution & Treatment Controls": ["water_infrastructure"],
    "Security & Protection Services": ["next_gen_cybersecurity"],

    # Telecom
    "Telecom Services": ["telecom_carriers"],
    "Telecommunications": ["telecom_carriers"],

    # Misc
    "Advertising Agencies": ["digital_advertising_adtech"],
    "Publishing": ["streaming_media_ott"],
    "Consulting Services": ["crm_enterprise_saas"],
    "Specialty Business Services": ["crm_enterprise_saas"],
    "Conglomerates": ["industrial_automation"],
    "Cannabis": ["cannabis"],
    "Tobacco": ["retail_stores"],
    "Lumber & Wood Production": ["construction_materials"],
    "Electronics & Computer Distribution": ["server_manufacturers"],
    "Home Improvement Retail": ["retail_stores"],
    "Residential Construction": ["construction_materials"],
    "Lodging": ["online_travel"],
}

# ─── Pre-process: Build lowercase keyword sets for each theme ──────────────
def tokenize(text):
    return text.lower() if text else ""

def match_keywords(text_lower, keywords):
    for kw in keywords:
        if kw.lower() in text_lower:
            return True
    return False

def match_negative(text_lower, neg_keywords):
    for kw in neg_keywords:
        if kw.lower() in text_lower:
            return True
    return False

def classify_by_text(text, name=""):
    """Returns list of matching theme_ids based on summary + name text."""
    if not text:
        return []
    combined = tokenize(text + " " + name)
    matches = []
    for theme_id, cfg in themes_config.items():
        pos_kws = cfg.get("keywords", [])
        neg_kws = cfg.get("negative_keywords", [])
        if not pos_kws:
            continue
        if match_keywords(combined, pos_kws):
            if not match_negative(combined, neg_kws):
                matches.append(theme_id)
    return matches

# ─── DB Connection ─────────────────────────────────────────────────────────
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ─── Step 0: Reset all theme_tags ─────────────────────────────────────────
print("=" * 70)
print("Step 0: theme_tags 초기화...")
cur.execute("UPDATE stock_metadata SET theme_tags = ''")
conn.commit()
cur.execute("SELECT COUNT(*) FROM stock_metadata")
total = cur.fetchone()[0]
print(f"  총 {total}개 종목 초기화 완료")

# ─── Helper: add tags ──────────────────────────────────────────────────────
def add_tags(ticker, new_tags):
    if not new_tags:
        return
    cur.execute("SELECT theme_tags FROM stock_metadata WHERE ticker = ?", (ticker,))
    row = cur.fetchone()
    if not row:
        return
    existing = set(t.strip() for t in (row[0] or "").split(",") if t.strip())
    updated = existing | set(new_tags)
    cur.execute(
        "UPDATE stock_metadata SET theme_tags = ?, last_updated = ? WHERE ticker = ?",
        (",".join(sorted(updated)), datetime.datetime.now().isoformat(), ticker)
    )

# ─── Step 1: premapped_tickers ────────────────────────────────────────────
print("\nStep 1: premapped_tickers 적용...")
premapped_count = 0
for theme_id, cfg in themes_config.items():
    for ticker in cfg.get("premapped_tickers", []):
        cur.execute("SELECT COUNT(*) FROM stock_metadata WHERE ticker = ?", (ticker,))
        if cur.fetchone()[0] > 0:
            add_tags(ticker, [theme_id])
            premapped_count += 1
conn.commit()
print(f"  premapped 적용 완료: {premapped_count}건")

# ─── Step 2: Summary keyword matching ─────────────────────────────────────
print("\nStep 2: Summary 키워드 매칭...")
cur.execute("""
    SELECT ticker, name, summary, industry 
    FROM stock_metadata 
    WHERE summary IS NOT NULL AND summary != 'FETCH_FAILED' AND summary != ''
""")
rows = cur.fetchall()
print(f"  요약 있는 종목: {len(rows)}개")

kw_classified = 0
for ticker, name, summary, industry in rows:
    tags = classify_by_text(summary, name or "")
    if tags:
        add_tags(ticker, tags)
        kw_classified += 1

conn.commit()
print(f"  키워드 분류 완료: {kw_classified}개 종목에 태그 추가")

# ─── Step 3: Industry fallback for still-unclassified stocks ──────────────
print("\nStep 3: Industry 기반 fallback 분류...")
cur.execute("""
    SELECT ticker, name, industry 
    FROM stock_metadata 
    WHERE (theme_tags = '' OR theme_tags IS NULL) 
    AND industry IS NOT NULL AND industry != ''
""")
unclassified = cur.fetchall()
print(f"  아직 미분류: {len(unclassified)}개")

industry_classified = 0
for ticker, name, industry in unclassified:
    if industry in INDUSTRY_THEME_MAP:
        tags = INDUSTRY_THEME_MAP[industry]
        add_tags(ticker, tags)
        industry_classified += 1

conn.commit()
print(f"  Industry fallback 분류: {industry_classified}개 종목")

# ─── Step 4: Name-based heuristic for remaining unclassified ──────────────
print("\nStep 4: 이름 기반 최후 분류...")
cur.execute("""
    SELECT ticker, name, industry 
    FROM stock_metadata 
    WHERE (theme_tags = '' OR theme_tags IS NULL)
""")
still_unclassified = cur.fetchall()
print(f"  여전히 미분류: {len(still_unclassified)}개")

NAME_HEURISTICS = [
    # Crypto
    (["bitcoin", "crypto", "blockchain", "digital asset", "mining corp"], "crypto_miners"),
    # Biotech/pharma (very broad)
    (["therapeutics", "oncology", "biopharma", "biosciences", "pharma", "gene therapy", "medical"], "pharmaceuticals_traditional"),
    # Tech
    (["software", "technologies", "tech inc", "digital", "cloud", "ai inc", "intelligence"], "crm_enterprise_saas"),
    # Finance
    (["bancorp", "bank", "financial", "capital", "fund", "investment", "holdings"], "asset_management"),
    # Real estate
    (["realty", "real estate", "reit", "properties", "property"], "reits_real_estate"),
    # Energy
    (["energy", "oil", "gas", "petroleum", "resources", "power corp"], "oil_gas_exploration"),
    # Mining
    (["mining", "minerals", "resources inc", "gold corp", "silver"], "rare_earth_elements"),
]

name_classified = 0
for ticker, name, industry in still_unclassified:
    name_lower = (name or "").lower()
    for keywords, theme in NAME_HEURISTICS:
        if any(kw in name_lower for kw in keywords):
            add_tags(ticker, [theme])
            name_classified += 1
            break

conn.commit()
print(f"  이름 기반 분류: {name_classified}개 종목")

# ─── Final Statistics ──────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("최종 분류 결과")
print("=" * 70)

cur.execute("SELECT COUNT(*) FROM stock_metadata WHERE theme_tags != '' AND theme_tags IS NOT NULL")
final_classified = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM stock_metadata WHERE theme_tags = '' OR theme_tags IS NULL")
final_unclassified = cur.fetchone()[0]

print(f"  분류 완료: {final_classified:,}개 / {total:,}개 ({final_classified/total*100:.1f}%)")
print(f"  미분류:    {final_unclassified:,}개")

# Theme breakdown
print("\n테마별 분류 현황 (상위 50개):")
cur.execute("SELECT ticker, theme_tags FROM stock_metadata WHERE theme_tags != ''")
all_tagged = cur.fetchall()
theme_counts = {}
for _, tags in all_tagged:
    for t in tags.split(","):
        t = t.strip()
        if t:
            theme_counts[t] = theme_counts.get(t, 0) + 1

sorted_themes = sorted(theme_counts.items(), key=lambda x: -x[1])
for tid, cnt in sorted_themes[:60]:
    name_ko = themes_config.get(tid, {}).get("name_ko", tid)
    print(f"  {tid:40s} {name_ko:30s} {cnt:4d}개")

# Check key themes for false positives
print("\n핵심 테마 정밀 검증:")
key_check = ["nand_memory", "server_manufacturers", "gpu_cloud_infrastructure",
             "power_generation_equipment", "smr_nuclear", "quantum_computing",
             "custom_ai_chips", "bitcoin_proxies", "uav_defense_drones"]
for tid in key_check:
    cur.execute("SELECT ticker, name FROM stock_metadata WHERE theme_tags LIKE ?", (f"%{tid}%",))
    rows2 = cur.fetchall()
    name_ko = themes_config.get(tid, {}).get("name_ko", tid)
    print(f"\n[{tid}] {name_ko} - {len(rows2)}개:")
    for ticker, name in rows2:
        print(f"  {ticker:8s} {(name or '')[:50]}")

conn.close()
print("\n\n전체 분류 완료!")
