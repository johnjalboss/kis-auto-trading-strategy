"""
reclassify_all.py - 전체 DB를 초기화하고 새 theme_db.json 기준으로 재분류
"""
import sqlite3
import json
import re
import os
import datetime

DB_PATH = "us_stocks_data.db"
THEME_DB_JSON = "theme_db.json"

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

# ────────────────────────────────────────────
# 1. 테마 설정 로드
# ────────────────────────────────────────────
with open(THEME_DB_JSON, "r", encoding="utf-8") as f:
    themes_config = json.load(f)["themes"]

# ────────────────────────────────────────────
# 2. DB 접속 및 모든 theme_tags 리셋
# ────────────────────────────────────────────
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("=== 기존 theme_tags 초기화 중... ===")
cur.execute("UPDATE stock_metadata SET theme_tags = ''")
conn.commit()
print(f"초기화 완료. 전체 종목 수: {cur.execute('SELECT COUNT(*) FROM stock_metadata').fetchone()[0]}")

# ────────────────────────────────────────────
# 3. premapped_tickers 먼저 적용
# ────────────────────────────────────────────
print("\n=== Step 1: premapped_tickers 적용 중... ===")
premapped_count = 0

for theme_id, cfg in themes_config.items():
    premapped = cfg.get("premapped_tickers", [])
    for ticker in premapped:
        cur.execute("SELECT theme_tags FROM stock_metadata WHERE ticker = ?", (ticker,))
        row = cur.fetchone()
        if row is None:
            continue
        existing = [t.strip() for t in row[0].split(",") if t.strip()] if row[0] else []
        if theme_id not in existing:
            existing.append(theme_id)
            cur.execute(
                "UPDATE stock_metadata SET theme_tags = ?, last_updated = ? WHERE ticker = ?",
                (",".join(existing), datetime.datetime.now().isoformat(), ticker)
            )
            premapped_count += 1

conn.commit()
print(f"premapped 적용: {premapped_count}개 매핑 완료")

# ────────────────────────────────────────────
# 4. keyword 기반 분류 (strict mode)
# ────────────────────────────────────────────
print("\n=== Step 2: 키워드 기반 분류 (strict) 중... ===")

# 각 테마별 EXCLUSION 집합 (다른 테마와 교차를 막기 위한 추가 규칙)
# 이 분류들은 오직 정확히 맞는 summary에만 적용
HIGH_SPECIFICITY_THEMES = {
    "nand_memory",
    "dram_memory",
    "server_manufacturers",
    "gpu_cloud_infrastructure",
    "power_generation_equipment",
    "quantum_computing",
    "crispr_gene_editing",
    "mrna_therapies",
    "lithography_equipment",
    "etching_deposition_equipment",
    "optical_interconnects",
    "custom_ai_chips",
    "smr_nuclear",
    "uranium_mining",
    "evtol_flying_cars",
    "solid_state_batteries",
    "humanoid_robotics",
    "glp1_weight_loss",
    "liquid_biopsy",
    "surgical_robotics",
    "hydrogen_fuel_cells",
    "solid_waste_recycling",
    "water_infrastructure",
    "crypto_miners",
    "bitcoin_proxies",
    "cannabis",
    "cultured_meat",
}

cur.execute("SELECT ticker, name, industry, summary, theme_tags FROM stock_metadata")
all_rows = cur.fetchall()

keyword_count = 0

for ticker, name, industry, summary, existing_tags in all_rows:
    if not summary or summary == "FETCH_FAILED":
        continue
    
    summary_lower = summary.lower()
    name_lower = (name or "").lower()
    industry_lower = (industry or "").lower()
    
    existing = [t.strip() for t in (existing_tags or "").split(",") if t.strip()]
    
    # 전반적 제외 필터: 이런 키워드가 있으면 테크 테마 적용 금지
    general_exclusions = [
        "consulting firm", "advisory firm", "law firm", "marketing agency",
        "holding company", "retail reseller", "distributor of products",
        "restaurant chain", "food service", "grocery"
    ]
    is_generic_non_tech = any(ex in summary_lower for ex in general_exclusions)
    
    # 🚫 업종별 테마 매핑 차단 규칙 (Forbidden Industries)
    financial_industries = {
        "asset management", "banks—regional", "banks—diversified", "capital markets",
        "insurance—specialty", "insurance—life", "insurance—property & casualty",
        "insurance brokers", "financial conglomerates", "credit services", "savings & cooperative banks",
        "finance", "financial services"
    }
    
    reit_industries = {
        "reit—diversified", "reit—office", "reit—retail", "reit—residential",
        "reit—industrial", "reit—specialty", "reit—healthcare", "reit—hotel & motel",
        "real estate services", "real estate—diversified", "real estate development", "real estate"
    }
    
    biotech_healthcare_industries = {
        "biotechnology", "drug manufacturers—general", "drug manufacturers—specialty & generic",
        "medical devices", "diagnostics & research", "medical instruments & supplies",
        "medical distribution", "healthcare plans"
    }
    
    retail_food_services = {
        "restaurants", "grocery stores", "apparel retail", "specialty retail",
        "department stores", "home improvement retail", "footwear & accessories retail",
        "discount stores", "travel services", "personal services"
    }

    oil_gas_services = {
        "oil & gas equipment & services", "oil & gas drilling", "oil & gas refining & marketing", "oil & gas midstream"
    }

    utility_industries = {
        "utilities—regulated electric", "utilities—regulated gas", "utilities—regulated water", "utilities—diversified", "utilities—independent power producers"
    }

    mining_industries = {
        "other industrial metals & mining", "gold", "silver", "copper", "aluminum"
    }

    industry_clean = (industry or "").lower().strip()
    
    # ─── 🚫 글로벌 텍스트 기반 금융/투자 회사 필터 (yfinance 업종 오류 보완) ───
    # BDC, 사모펀드, 벤처캐피탈, 자산운용사 등이 요약문 텍스트에 포함되어 있는 경우
    investment_text_indicators = [
        "closed-end management investment company",
        "business development company",
        "private equity firm",
        "venture capital firm",
        "mutual fund",
        "etf provider",
        "investment trust",
        "specializes in private equity",
        "specializes in venture capital",
        "specializes in debt investments",
        "specializes in credit and private equity"
    ]
    is_investment_firm_text = any(indicator in summary_lower for indicator in investment_text_indicators)
    
    # 1. 금융/자산운용 업종 또는 요약문 기준 금융투자회사 -> 금융/핀테크/크립토 테마를 제외한 모든 테마 차단
    financial_allowed_themes = {
        "regional_banks", "insurance", "asset_management", "payments_fintech", 
        "bnpl_lending_fintech", "trading_brokerage", "bitcoin_proxies", "crypto_miners"
    }
    is_financial_industry = any(fi in industry_clean for fi in financial_industries) or is_investment_firm_text
    
    # 2. 리츠/부동산 업종 종목 -> 부동산 관련 테마를 제외한 모든 테마 차단
    reit_allowed_themes = {"reits_real_estate", "datacenter_reits"}
    is_reit_industry = any(ri in industry_clean for ri in reit_industries)
    
    # 3. 제약/바이오 업종 종목 -> 헬스케어 관련 테마를 제외한 모든 테마 차단
    healthcare_allowed_themes = set(THEME_CATEGORIES["🧬 헬스케어 & 바이오"])
    is_biotech_industry = any(bi in industry_clean for bi in biotech_healthcare_industries)
    
    # 4. 소매/음식점 업종 종목 -> 소비재 관련 테마를 제외한 모든 테마 차단
    consumer_retail_allowed_themes = set(THEME_CATEGORIES["📺 소비자 & 미디어"]) | {"retail_stores", "restaurants_food"}
    is_retail_industry = any(ri in industry_clean for ri in retail_food_services)

    # 5. 석유/가스 서비스 업종 종목 -> 에너지 관련 테마를 제외한 모든 테마 차단 (통신, 폐기물, 자산운용 등 오분류 방지)
    energy_allowed_themes = {
        "oil_gas_exploration", "pipeline_midstream", "lng_natural_gas", 
        "power_generation_equipment", "power_grid_transformers", "carbon_capture"
    }
    is_oil_gas_service = any(og in industry_clean for og in oil_gas_services)

    # 6. 광업 업종 종목 -> 원자재/소재 관련 외의 모든 테마 차단
    mining_allowed_themes = {
        "copper_mining", "lithium_mining", "rare_earth_elements", "steel_metals", "uranium_mining"
    }
    is_mining_industry = any(mi in industry_clean for mi in mining_industries)

    new_tags_to_add = []
    
    # 🚫 수동으로 매핑된 확정(premapped) 테마가 하나라도 있다면, 
    # 동음이의어로 인한 오분류(예: NVDA가 자동차로 분류되는 등)를 방지하기 위해 키워드 매칭을 스킵합니다.
    has_any_premapped = False
    for tid, tcfg in themes_config.items():
        if ticker in tcfg.get("premapped_tickers", []):
            has_any_premapped = True
            break
            
    if not has_any_premapped:
        for theme_id, cfg in themes_config.items():
            if theme_id in existing:
                continue  # 이미 premapped으로 할당됨
            
        # 🚫 업종별 테마 매핑 원천 차단 규칙 적용
        if is_financial_industry and theme_id not in financial_allowed_themes:
            continue
        if is_reit_industry and theme_id not in reit_allowed_themes:
            continue
        if is_biotech_industry and theme_id not in healthcare_allowed_themes:
            continue
        if is_retail_industry and theme_id not in consumer_retail_allowed_themes:
            continue
        if is_oil_gas_service and theme_id not in energy_allowed_themes:
            continue
        if is_mining_industry and theme_id not in mining_allowed_themes:
            continue

        # 개별 테마별 세부 업종 매칭 가드 (동음이의어 방지)
        # 통신사 테마: wireline 등의 키워드가 통신 업종이 아닐 경우 매핑 방지
        if theme_id == "telecom_carriers" and not any(x in industry_clean for x in ["telecom", "communication", "internet"]):
            continue
        # 폐기물 재활용 테마: waste management, environmental 등 관련 업종만 허용
        if theme_id == "solid_waste_recycling" and not any(x in industry_clean for x in ["waste", "environmental", "utilities"]):
            continue
        # 수자원/수처리 테마: 석유 서비스 및 타 에너지 업종 차단
        if theme_id == "water_infrastructure" and any(x in industry_clean for x in ["oil", "gas", "energy", "petroleum"]):
            continue
        
        keywords = cfg.get("keywords", [])
        negative_keywords = cfg.get("negative_keywords", [])
        
        # high-specificity 테마는 특히 엄격하게 처리
        if theme_id in HIGH_SPECIFICITY_THEMES and is_generic_non_tech:
            continue
        
        # 부정 키워드 체크 (이 키워드가 있으면 이 테마 불가)
        has_negative = any(neg.lower() in summary_lower for neg in negative_keywords)
        if has_negative:
            continue
        
        # 긍정 키워드 체크 - 모든 키워드는 단어 경계 매칭
        matched = False
        for kw in keywords:
            pattern = r'(?<!\w)' + re.escape(kw.lower()) + r'(?!\w)'
            if re.search(pattern, summary_lower):
                matched = True
                break
        
        if matched:
            new_tags_to_add.append(theme_id)
    
    if new_tags_to_add:
        all_tags = list(set(existing + new_tags_to_add))
        cur.execute(
            "UPDATE stock_metadata SET theme_tags = ?, last_updated = ? WHERE ticker = ?",
            (",".join(all_tags), datetime.datetime.now().isoformat(), ticker)
        )
        keyword_count += 1

conn.commit()
print(f"키워드 분류: {keyword_count}개 종목 업데이트")

# ────────────────────────────────────────────
# 5. 결과 검증 출력
# ────────────────────────────────────────────
print("\n=== 검증: 주요 종목 분류 결과 ===")
test_tickers = ["GEV", "DELL", "SMCI", "CRWV", "CRWD", "MU", "WDC", "SNDK", 
                "NVDA", "ANET", "VRT", "ETN", "CEG", "OKLO", "MSTR", "MARA",
                "CRSP", "LLY", "ISRG", "AMZN"]

for ticker in test_tickers:
    cur.execute("SELECT name, theme_tags FROM stock_metadata WHERE ticker = ?", (ticker,))
    row = cur.fetchone()
    if row:
        themes_list = row[1] if row[1] else "(미분류)"
        print(f"  {ticker:8s} | {row[0][:35]:35s} | {themes_list}")
    else:
        print(f"  {ticker:8s} | (DB에 없음)")

# ────────────────────────────────────────────
# 6. 각 테마별 종목 수 통계
# ────────────────────────────────────────────
print("\n=== 테마별 분류 현황 ===")
theme_stats = {}
cur.execute("SELECT theme_tags FROM stock_metadata WHERE theme_tags != ''")
for (tags_str,) in cur.fetchall():
    for tag in tags_str.split(","):
        tag = tag.strip()
        if tag:
            theme_stats[tag] = theme_stats.get(tag, 0) + 1

# 정렬해서 출력
for theme_id in sorted(theme_stats, key=lambda x: theme_stats[x], reverse=True):
    cfg = themes_config.get(theme_id, {})
    name_ko = cfg.get("name_ko", theme_id)
    name_en = cfg.get("name_en", theme_id)
    count = theme_stats[theme_id]
    print(f"  {theme_id:35s} {name_ko:25s} {count:4d}개 종목")

# 미분류 종목 수
cur.execute("SELECT COUNT(*) FROM stock_metadata WHERE theme_tags = '' OR theme_tags IS NULL")
unclassified = cur.fetchone()[0]
print(f"\n  미분류: {unclassified}개")

print("\n=== nand_memory 전체 목록 (false positive 확인) ===")
cur.execute("SELECT ticker, name FROM stock_metadata WHERE theme_tags LIKE '%nand_memory%'")
nand_stocks = cur.fetchall()
print(f"nand_memory 분류 종목 총 {len(nand_stocks)}개:")
for ticker, name in nand_stocks:
    print(f"  {ticker:8s} {name}")

conn.close()
print("\n=== 재분류 완료 ===")
