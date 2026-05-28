import os

def clean_file(path):
    print(f"Cleaning {path}...")
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Read error: {e}")
        return
    
    clean_lines = []
    for line in lines:
        # Replace non-ASCII with a space to preserve string structure
        clean_line = "".join(i if ord(i) < 128 else " " for i in line)
        clean_lines.append(clean_line)
        
    with open(path, 'w', encoding='ascii', newline='\n') as f:
        f.writelines(clean_lines)

if __name__ == "__main__":
    files = [
        r'C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading\strategy.py',
        r'C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading\composite_signal.py',
        r'C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading\orchestrator.py'
    ]
    
    for f in files:
        clean_file(f)
    print("Done.")

