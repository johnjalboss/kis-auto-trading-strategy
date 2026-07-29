import json

with open("theme_db.json", "r", encoding="utf-8") as f:
    data = json.load(f)

traditional_themes = {
    "regional_banks": {
        "name_en": "Regional Banks & Lending",
        "name_ko": "지역 은행 및 여신",
        "keywords": ["bank", "banking", "regional bank", "savings and loan", "credit union", "lending bank"],
        "premapped_tickers": ["JPM", "BAC", "WFC", "C", "MS", "GS", "PNC", "TFC", "USB", "FITB"]
    },
    "insurance": {
        "name_en": "Insurance Carriers",
        "name_ko": "보험사",
        "keywords": ["insurance", "reinsurance", "underwriting", "policyholder", "property and casualty"],
        "premapped_tickers": ["BRK.B", "BRK.A", "MET", "PRU", "ALL", "PGR", "CB", "AIG", "TRV"]
    },
    "reits_real_estate": {
        "name_en": "Real Estate & REITs",
        "name_ko": "부동산 및 리츠",
        "keywords": ["reit", "real estate", "reits", "property management", "leasing property", "real estate investment trust"],
        "premapped_tickers": ["PLD", "AMT", "CCI", "EQIX", "O", "SPG", "WY", "PSA", "DLR"]
    },
    "asset_management": {
        "name_en": "Asset Management & Investment Services",
        "name_ko": "자산운용 및 투자 서비스",
        "keywords": ["asset management", "wealth management", "brokerage", "investment firm", "private equity", "financial advisory"],
        "premapped_tickers": ["BLK", "BX", "KKR", "APO", "TROW", "BEN"]
    },
    "restaurants_food": {
        "name_en": "Restaurants & Food Services",
        "name_ko": "외식 및 식음료 서비스",
        "keywords": ["restaurant", "diners", "coffee shop", "fast food", "cafeteria", "quick service restaurant"],
        "premapped_tickers": ["MCD", "SBUX", "YUM", "CMG", "DPZ", "DRI", "WEN"]
    },
    "retail_stores": {
        "name_en": "Retail & Department Stores",
        "name_ko": "소매 및 유통",
        "keywords": ["retail", "department store", "supermarket", "grocery store", "e-commerce retail", "apparel retail", "wholesaler"],
        "premapped_tickers": ["WMT", "COST", "TGT", "HD", "LOW", "TJX", "KR", "DG"]
    },
    "oil_gas_exploration": {
        "name_en": "Oil & Gas E&P",
        "name_ko": "석유 및 가스 시추",
        "keywords": ["oil and gas", "exploration and production", "drilling", "natural gas exploration", "crude oil", "petroleum"],
        "premapped_tickers": ["XOM", "CVX", "COP", "EOG", "SLB", "HAL", "MPC", "PSX", "VLO"]
    },
    "utilities_traditional": {
        "name_en": "Traditional Utilities",
        "name_ko": "전통 유틸리티 발전",
        "keywords": ["utility", "electric utility", "gas utility", "water utility", "regulated utility"],
        "premapped_tickers": ["NEE", "SO", "DUK", "AEP", "D", "EXC", "SRE", "XEL"]
    },
    "steel_metals": {
        "name_en": "Steel & Metals Manufacturing",
        "name_ko": "철강 및 금속 제조",
        "keywords": ["steel", "aluminum", "metal fabrication", "mining iron", "metallurgical"],
        "premapped_tickers": ["NUE", "STLD", "X", "AA", "FCX", "CLF"]
    },
    "auto_manufacturers": {
        "name_en": "Auto Manufacturers",
        "name_ko": "자동차 제조",
        "keywords": ["automobile", "automotive", "car manufacturer", "truck manufacturing", "vehicle assembly"],
        "premapped_tickers": ["F", "GM", "TSLA", "STLA", "HMC", "TM"]
    },
    "air_freight_logistics": {
        "name_en": "Air Freight & Logistics",
        "name_ko": "물류 및 화물 운송",
        "keywords": ["air freight", "logistics service", "trucking", "shipping cargo", "freight forwarding", "railroad"],
        "premapped_tickers": ["UPS", "FDX", "UNP", "CSX", "NSC"]
    },
    "apparel_footwear": {
        "name_en": "Apparel & Footwear",
        "name_ko": "의류 및 신발 제조",
        "keywords": ["apparel", "footwear", "clothing", "garment", "shoes", "athletic apparel"],
        "premapped_tickers": ["NKE", "LULU", "RL", "PVH", "VFC", "SKX"]
    },
    "household_personal": {
        "name_en": "Household & Personal Products",
        "name_ko": "생활용품 및 화장품",
        "keywords": ["household product", "cosmetic", "personal care", "toiletries", "beauty product", "detergent", "soap"],
        "premapped_tickers": ["PG", "EL", "CL", "KMB", "CHD", "COTY"]
    },
    "pharmaceuticals_traditional": {
        "name_en": "Traditional Pharmaceuticals",
        "name_ko": "전통 제약사",
        "keywords": ["pharmaceutical", "drug manufacturer", "generic drug", "over-the-counter drug"],
        "premapped_tickers": ["PFE", "JNJ", "MRK", "BMY", "ABBV", "ABT"]
    }
}

data["themes"].update(traditional_themes)

with open("theme_db.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Successfully added {len(traditional_themes)} traditional themes to theme_db.json.")
