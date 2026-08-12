#!/usr/bin/env python3
"""Cloudflare Tunnel Manager for Web Dashboard"""
import subprocess
import time
import re
import os

LOG_FILE = "/home/ubuntu/kis-auto-trading/logs/tunnel.log"
URL_FILE = "/home/ubuntu/kis-auto-trading/logs/tunnel_url.txt"

def start_tunnel():
    os.makedirs("/home/ubuntu/kis-auto-trading/logs", exist_ok=True)
    subprocess.run("pkill -9 -f cloudflared", shell=True)
    
    cmd = "/tmp/cloudflared tunnel --url http://localhost:8080"
    with open(LOG_FILE, "w") as f:
        proc = subprocess.Popen(cmd, shell=True, stdout=f, stderr=f)
    
    print(f"Cloudflared process launched PID: {proc.pid}")
    
    # Wait for URL to appear in log
    for _ in range(15):
        time.sleep(1)
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                content = f.read()
                match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", content)
                if match:
                    url = match.group(0)
                    print(f"✅ TUNNEL_URL_FOUND: {url}")
                    with open(URL_FILE, "w") as uf:
                        uf.write(url)
                    return url
    print("⚠️ Tunnel URL not found yet.")
    return None

if __name__ == "__main__":
    start_tunnel()
