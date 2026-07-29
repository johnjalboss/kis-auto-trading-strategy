if __name__ == "__main__":
    with open(r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading\orchestrator.py", "r", encoding="utf-8") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if "correlation_regime" in line or "CorrelationRegimeDetector" in line:
            print(f"Line {i+1}: {line.strip()}")
            # print surrounding 5 lines
            start = max(0, i - 5)
            end = min(len(lines), i + 6)
            for j in range(start, end):
                print(f"  {j+1}: {lines[j].strip()}")
            print("-" * 50)

