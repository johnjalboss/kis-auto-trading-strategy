"""
verify_all_themes.py - 모든 테마의 분류를 검증
"""
import sqlite3
import json
import sys
import io

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB_PATH = "us_stocks_data.db"
THEME_DB_JSON = "theme_db.json"

with open(THEME_DB_JSON, "r", encoding="utf-8") as f:
    themes_config = json.load(f)["themes"]

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

output_lines = []

for theme_id, cfg in themes_config.items():
    name_ko = cfg.get("name_ko", theme_id)
    name_en = cfg.get("name_en", theme_id)
    
    cur.execute(
        "SELECT ticker, name, industry, summary FROM stock_metadata WHERE theme_tags LIKE ?",
        (f"%{theme_id}%",)
    )
    rows = cur.fetchall()
    
    if not rows:
        output_lines.append(f"\n[{theme_id}] {name_ko} -- 분류 종목 없음")
        continue
    
    output_lines.append(f"\n{'='*70}")
    output_lines.append(f"[{theme_id}] {name_ko} / {name_en}")
    output_lines.append(f"  총 {len(rows)}개 종목")
    output_lines.append("="*70)
    
    for ticker, name, industry, summary in rows:
        summary_short = (summary or "")[:120].replace("\n", " ")
        output_lines.append(f"  {ticker:8s} | {(name or '')[:40]:40s} | {(industry or '')[:28]:28s}")
        if summary_short:
            output_lines.append(f"           >> {summary_short}")
        output_lines.append("")

conn.close()

for line in output_lines:
    print(line)

print("\n검증 완료")
