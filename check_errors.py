import os

log_path = os.path.expanduser("~/kis-auto-trading/logs/trading_bot.log")

try:
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
        
    recent_lines = lines[-5000:]
    
    print("--- MODULE LOAD SUMMARY ---")
    for line in recent_lines:
        if "Phase 1 Complete" in line or "Exception" in line or "ModuleNotFoundError" in line or ("skipped" in line and "->" in line):
            print(line.strip()[:200])
            
    print("\n--- RECENT ERRORS (last 20) ---")
    error_lines = [l.strip()[:200] for l in recent_lines if "ERROR" in l or "FATAL" in l or "Exception" in l or ("error" in l.lower() and "DEBUG" not in l)]
    for e in error_lines[-20:]:
        print(e)
        
except Exception as e:
    print(f"Failed to read logs: {e}")
