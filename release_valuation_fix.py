import os
import shutil
import json
import subprocess

SRC_DIR = r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading"
DST_DIR = r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading-packaged"

# Core files to sync (including fundamental_analyzer.py)
SYNC_FILES = [
    'fundamental_analyzer.py',
    'version.json'
]

def main():
    print("=" * 60)
    print("STARTING RELEASE PACKAGER v1.7.4 (FOR FRIENDS)")
    print("=" * 60)
    
    # 1. Copy files
    print("\n[1/3] Copying updated files to packaged directory...")
    copied_count = 0
    for f in SYNC_FILES:
        src_path = os.path.join(SRC_DIR, f)
        dst_path = os.path.join(DST_DIR, f)
        if os.path.exists(src_path):
            shutil.copy2(src_path, dst_path)
            print(f"  OK   {f}")
            copied_count += 1
        else:
            print(f"  SKIP {f} (not found in source)")
            
    print(f"  Total copied: {copied_count}/{len(SYNC_FILES)}")
    
    # 2. Update version.json version in target dir just in case
    print("\n[2/3] Verifying and updating version.json to v1.7.4...")
    version_path = os.path.join(DST_DIR, "version.json")
    
    packaged_files = []
    for f in os.listdir(DST_DIR):
        if f.endswith('.py') or f == 'requirements.txt':
            packaged_files.append(f)
    packaged_files = sorted(list(set(packaged_files)))
    
    version_data = {
        "version": "1.7.4",
        "files": packaged_files
    }
    
    with open(version_path, "w", encoding="utf-8") as f:
        json.dump(version_data, f, indent=2, ensure_ascii=False)
        
    print(f"  Saved version.json with {len(packaged_files)} tracked files.")
    
    # 3. Git commit & push
    print("\n[3/3] Committing and pushing to GitHub packaged repo...")
    subprocess.run(["git", "add", "."], cwd=DST_DIR)
    
    commit_msg = "feat: v1.7.4 - Upgrade fundamental analyzer valuation model with PEG and sector-based PE normalization"
    res = subprocess.run(["git", "commit", "-m", commit_msg], cwd=DST_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("  Commit output:")
    print(res.stdout.decode('utf-8', errors='ignore'))
    
    print("  Pushing to GitHub origin main...")
    res_push = subprocess.run(["git", "push", "origin", "main"], cwd=DST_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("  Push output:")
    print(res_push.stdout.decode('utf-8', errors='ignore'))
    print(res_push.stderr.decode('utf-8', errors='ignore'))
    
    print("=" * 60)
    print("RELEASE PACKAGER v1.7.4 COMPLETED SUCCESS!")
    print("=" * 60)

if __name__ == '__main__':
    main()
