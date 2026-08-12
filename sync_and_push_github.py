"""
GitHub Auto-Sync & Push Script (sync_and_push_github.py)
==========================================================
Synchronizes all latest code from kis-auto-trading to kis-auto-trading-packaged
and pushes to GitHub repository: johnjalboss/kis-auto-trading-strategy
"""

import os
import shutil
import subprocess

SOURCE_DIR = r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading"
PACKAGED_DIR = r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading-packaged"

# Files/folders to exclude from copying
EXCLUDE = {
    ".git", ".env", "venv", "__pycache__", "trades.db", "token.json", "logs", "backups", "scratch"
}

def sync_files():
    print(f"[SYNC] Synchronizing {SOURCE_DIR} -> {PACKAGED_DIR}")
    for item in os.listdir(SOURCE_DIR):
        if item in EXCLUDE or item.endswith(".pyc") or item.endswith(".log"):
            continue

        src_path = os.path.join(SOURCE_DIR, item)
        dst_path = os.path.join(PACKAGED_DIR, item)

        if os.path.isfile(src_path):
            shutil.copy2(src_path, dst_path)
            print(f"  [COPY] {item}")
        elif os.path.isdir(src_path):
            if os.path.exists(dst_path):
                shutil.rmtree(dst_path)
            shutil.copytree(src_path, dst_path, ignore=shutil.ignore_patterns("*.pyc", "__pycache__"))
            print(f"  [DIR] {item}")

def push_to_github():
    print("\n[PUSH] Pushing to GitHub (johnjalboss/kis-auto-trading-strategy)...")
    try:
        subprocess.run(["git", "add", "."], cwd=PACKAGED_DIR, check=True)

        commit_msg = "feat: Update latest 4 quant upgrades, 3 proposal modules & 5-position sizing"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=PACKAGED_DIR, capture_output=True, text=True)

        res = subprocess.run(["git", "push", "origin", "main"], cwd=PACKAGED_DIR, capture_output=True, text=True)
        if res.returncode == 0:
            print("[OK] Successfully pushed to GitHub (johnjalboss/kis-auto-trading-strategy)!")
        else:
            print(f"[WARN] Git push output: {res.stdout}\n{res.stderr}")
    except Exception as e:
        print(f"[FAIL] Git push error: {e}")

if __name__ == "__main__":
    sync_files()
    push_to_github()
