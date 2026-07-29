import os

log_file = "latest_remote_log.txt"
out_file = "info_only.txt"

if os.path.exists(log_file):
    with open(log_file, "r", encoding="utf16", errors="ignore") as f:
        lines = f.readlines()
        
    info_lines = [line.strip() for line in lines if "INFO" in line]
    
    with open(out_file, "w", encoding="utf8") as f:
        for line in info_lines:
            f.write(line + "\n")
    print(f"Written {len(info_lines)} lines to {out_file}")
else:
    print(f"File {log_file} not found")
