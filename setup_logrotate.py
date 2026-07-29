#!/usr/bin/env python3
"""
setup_logrotate.py
서버에서 실행하면 logrotate 설정을 자동으로 구성합니다.
- 매일 자정 로그 회전
- 7일치만 보관 후 자동 삭제 (gzip 압축)
- 봇 서비스 무중단 (copytruncate)
"""
import subprocess, os

config = """/home/ubuntu/kis-auto-trading/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    maxsize 50M
}
"""

config_path = "/etc/logrotate.d/kis-trading"

try:
    with open("/tmp/kis_logrotate.conf", "w") as f:
        f.write(config)
    
    subprocess.run(["sudo", "cp", "/tmp/kis_logrotate.conf", config_path], check=True)
    subprocess.run(["sudo", "chmod", "644", config_path], check=True)
    
    # 즉시 한 번 실행하여 현재 비대한 로그 압축
    result = subprocess.run(
        ["sudo", "logrotate", "-f", config_path],
        capture_output=True, text=True
    )
    print("✅ logrotate 설정 완료!")
    print(f"설정 파일: {config_path}")
    print("📋 정책: 매일 회전, 7일 보관, gzip 압축, 50MB 초과시 즉시 회전")
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr[:300])
        
    # 현재 로그 파일 크기 확인
    result2 = subprocess.run(
        ["du", "-sh", "/home/ubuntu/kis-auto-trading/remote_trading_bot.log",
         "/home/ubuntu/kis-auto-trading/bot_error.log"],
        capture_output=True, text=True
    )
    print("\n📊 현재 로그 크기:")
    print(result2.stdout)

except Exception as e:
    print(f"❌ 설정 실패: {e}")
