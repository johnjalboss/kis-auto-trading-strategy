import re
import sys

log_file = "remote_trading_bot_latest.log"

try:
    with open(log_file, "r", encoding="utf-8") as f, open("rlmd_analysis.txt", "w", encoding="utf-8") as out:
        lines = f.readlines()
        
        out.write("--- RLMD Trade Events ---\n")
        for i, line in enumerate(lines):
            if "RLMD" in line or "rlmd" in line:
                # Print the line itself
                out.write(f"L{i}: {line.strip()}\n")
                
                # If it's a BUY, STOP, EXIT, or Order Executed, print context
                if any(keyword in line for keyword in ["BUY", "SELL", "EXIT", "STOP", "Order Executed", "OrderResult", "P&L"]):
                    out.write("-" * 40 + "\n")

    print("Success writing to rlmd_analysis.txt")
except FileNotFoundError:
    print(f"File {log_file} not found locally.")
except Exception as e:
    print(f"Error reading file: {e}")
