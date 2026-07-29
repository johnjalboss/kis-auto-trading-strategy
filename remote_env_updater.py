import re

env_path = "/home/ubuntu/kis-auto-trading/.env"
with open(env_path, "r", encoding="utf-8") as f:
    content = f.read()

updates = {
    "MAX_POSITIONS": "3",
    "UPGRADE_MIN_HOLD_MINUTES": "120",
    "UPGRADE_SCORE_GAP": "25",
    "UPGRADE_MAX_PER_DAY": "5",
    "UPGRADE_PROFIT_PROTECT_PCT": "0.02"
}

for key, val in updates.items():
    pattern = rf"^{key}=.*$"
    replacement = f"{key}={val}"
    if re.search(pattern, content, flags=re.MULTILINE):
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    else:
        content += f"\n{key}={val}"

with open(env_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Remote .env updated successfully via script!")
