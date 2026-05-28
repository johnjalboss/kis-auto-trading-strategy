import sys
import os

if __name__ == "__main__":
    filepath = '/home/ubuntu/kis-auto-trading/remote_trading_bot.log'
    if not os.path.exists(filepath):
        print(f"Log file not found: {filepath}")
        sys.exit(1)
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
        for line in lines[-500:]:
            sys.stdout.write(line)

