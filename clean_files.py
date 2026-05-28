import os

def clean_file(path):
    with open(path, 'rb') as f:
        content = f.read()
    
    # Remove BOM
    if content.startswith(b'\xef\xbb\xbf'):
        content = content[3:]
    
    # Try to decode as utf-8, then strip non-ascii
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        text = content.decode('latin-1')
    
    # Filter out non-ASCII
    clean_text = "".join(i for i in text if ord(i) < 128)
    
    with open(path, 'w', encoding='ascii', newline='\n') as f:
        f.write(clean_text)

if __name__ == "__main__":
    files = [
        r'C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading\strategy.py',
        r'C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading\composite_signal.py',
        r'C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading\orchestrator.py'
    ]
    
    for f in files:
        print(f"Cleaning {f}...")
        clean_file(f)

