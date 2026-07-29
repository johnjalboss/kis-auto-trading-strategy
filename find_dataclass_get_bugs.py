import os

if __name__ == "__main__":
    root_dir = r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading"
    search_pattern = ".get('regime'"

    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if search_pattern in content:
                            print(f"Found buggy pattern in: {path}")
                            # print the lines
                            lines = content.splitlines()
                            for i, line in enumerate(lines):
                                if search_pattern in line:
                                    print(f"  Line {i+1}: {line}")
                except Exception:
                    pass

