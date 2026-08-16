import subprocess

service_content = """[Unit]
Description=US Theme Radar 24/7 Autonomous Real-Time Engine
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/us-theme-tracker
ExecStart=/usr/bin/python3 /home/ubuntu/us-theme-tracker/theme_radar_daemon.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

with open("theme-radar.service", "w", encoding="utf-8") as f:
    f.write(service_content)

print("Created theme-radar.service")
