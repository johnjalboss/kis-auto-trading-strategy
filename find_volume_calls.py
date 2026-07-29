import os

if __name__ == "__main__":
    for root, dirs, files in os.walk('.'):
        for f in files:
            if f.endswith('.py'):
                path = os.path.join(root, f)
                try:
                    with open(path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        if 'Volume' in content or 'volume' in content:
                            # Find lines with yf.download or download or Ticker or TickerProxy
                            lines = content.split('\n')
                            for idx, line in enumerate(lines):
                                if any(k in line for k in ['download', 'Ticker', 'analyze']):
                                    if any(v in line for v in ["'Volume'", '"Volume"', "'VOLUME'", '"VOLUME"']):
                                        print(f"{path}:{idx+1} -> {line}")
                except Exception:
                    pass

