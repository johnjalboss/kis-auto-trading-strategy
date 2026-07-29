import json

with open("theme_db.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 1. Update nand_memory to be extremely precise
data["themes"]["nand_memory"] = {
    "name_en": "NAND Flash Memory",
    "name_ko": "NAND 플래시 메모리",
    "keywords": ["nand", "flash memory", "ssd controller", "solid-state drive", "solid state drive", "ssd storage", "nand storage"],
    "premapped_tickers": ["WDC", "MU", "STX", "PSTG"],
    "negative_keywords": ["energy storage", "battery storage", "grid storage", "cloud security", "cybersecurity", "server", "servers", "advisory", "software developer"]
}

# 2. Add negative keywords to other key tech themes to prevent overlaps
data["themes"]["dram_memory"]["negative_keywords"] = ["server", "servers", "cloud security", "software", "energy storage"]
data["themes"]["custom_ai_chips"]["negative_keywords"] = ["software", "cybersecurity", "cloud", "consulting"]
data["themes"]["optical_interconnects"]["negative_keywords"] = ["software", "biotech", "medical", "regional bank"]
data["themes"]["smr_nuclear"]["negative_keywords"] = ["medical", "agricultural", "software", "retail"]
data["themes"]["power_grid_transformers"]["negative_keywords"] = ["solar panel", "wind turbine", "software", "pharmaceutical"]
data["themes"]["datacenter_liquid_cooling"]["negative_keywords"] = ["solar", "car maker", "software", "biotech"]
data["themes"]["telehealth"]["negative_keywords"] = ["semiconductor", "mining", "steel", "oil"]
data["themes"]["autonomous_driving"]["negative_keywords"] = ["software asset", "accounting", "retailer", "banking"]

with open("theme_db.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Successfully sanitized keywords and added negative keywords to theme_db.json.")
