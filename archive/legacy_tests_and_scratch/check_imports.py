import os

def check_files():
    root_dir = "."
    results = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if "config." in content and "import config" not in content:
                            results.append(path)
                except Exception as err:
                    print("⚠️ [check_imports.py] Fallback triggered:", err)
    return results

if __name__ == "__main__":
    missing = check_files()
    if missing:
        print("\n".join(missing))
    else:
        print("None found")
