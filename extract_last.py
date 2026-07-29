import os

log_file = "latest_remote_log.txt"
out_file = "last_200_lines.txt"

if os.path.exists(log_file):
    # Trying utf-16le first
    try:
        with open(log_file, "r", encoding="utf16", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        with open(log_file, "r", encoding="utf8", errors="ignore") as f:
            lines = f.readlines()
            
    with open(out_file, "w", encoding="utf8") as f:
        for line in lines[-200:]:
            f.write(line.strip() + "\n")
    print(f"Written last 200 lines to {out_file}")
else:
    print(f"File {log_file} not found")
