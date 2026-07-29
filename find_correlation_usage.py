import os

if __name__ == "__main__":
    search_terms = ["correlation_regime", "CorrelationRegimeDetector"]
    root_dir = r"C:\Users\wngud\AppData\Local\Temp" # wait, the workspace is scratch/kis-auto-trading
    workspace_dir = r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading"

    print(f"Searching for terms {search_terms} in {workspace_dir}...")

    for root, dirs, files in os.walk(workspace_dir):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                        for term in search_terms:
                            if term in content:
                                print(f"Found term '{term}' in file: {path}")
                except Exception as e:
                    pass

