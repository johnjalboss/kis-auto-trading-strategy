"""
AI 스윙 트레이딩 봇 - 지능형 자동 업데이트 엔진 (updater.py)
======================================================
사용자가 깃허브(GitHub) 등에 최신 전략 코드를 올려두면,
지인들이 프로그램을 더블클릭해 가동할 때 자동으로 원격 서버와 대조하여
최신 알고리즘 파일들을 덮어쓰기 다운로드해 주는 무인 자동 업데이트 솔루션입니다.
"""

import os
import json
import requests
from loguru import logger

# ----------------------------------------------------
# ⚠️ 중요: 본인의 깃허브 저장소 주소에 맞게 아래 주소를 변경하십시오.
# ----------------------------------------------------
# 예: https://raw.githubusercontent.com/[깃허브ID]/[저장소이름]/main/
RAW_BASE_URL = "https://raw.githubusercontent.com/johnjalboss/kis-auto-trading-strategy/main/"
VERSION_FILE = "version.json"

def check_and_update() -> bool:
    """원격 저장소와 버전을 비교하여 최신 전략 파일들을 자동 다운로드 및 덮어쓰기합니다."""
    
    # 1. 로컬 버전 로드
    local_version = "1.0.0"
    local_files = ["strategy.py", "orchestrator.py", "screener.py", "indicators.py"]
    
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                local_version = data.get("version", "1.0.0")
                local_files = data.get("files", local_files)
        except Exception as e:
            logger.debug("로컬 버전 파일 로드 실패 (기본값 적용): {}", e)
            
    # 2. 원격 버전 조회
    remote_version_url = RAW_BASE_URL + VERSION_FILE
    try:
        res = requests.get(remote_version_url, timeout=5)
        if res.status_code != 200:
            logger.info("?? 오프라인 또는 원격 업데이트 서버가 활성화되지 않았습니다. 기존 로컬 전략으로 가동합니다.")
            return False
        
        remote_data = res.json()
        remote_version = remote_data.get("version", "1.0.0")
        remote_files = remote_data.get("files", local_files)
    except Exception as e:
        logger.info("?? 네트워크 오프라인 상태이거나 업데이트 서버가 점검 중입니다. (기존 버전 {} 가동)", local_version)
        return False
        
    # 3. 버전 비교
    if remote_version == local_version:
        logger.info("✅ 현재 최신 버전({}) 전략을 사용 중입니다. 업데이트가 필요 없습니다.", local_version)
        return False
        
    logger.warning("?? 새 업데이트 감지! [로컬 v{}] -> [최신 v{}]", local_version, remote_version)
    logger.info("?? 최신 알고리즘 패치 파일 {}개를 자동으로 동기화합니다...", len(remote_files))
    
    # 4. 파일 다운로드 및 안전 덮어쓰기
    updated_count = 0
    for file_name in remote_files:
        file_url = RAW_BASE_URL + file_name
        try:
            logger.info("   -> {} 다운로드 및 덮어쓰기 중...", file_name)
            file_res = requests.get(file_url, timeout=8)
            if file_res.status_code == 200:
                # 임시 파일로 먼저 저장하여 안전성 확보
                temp_name = file_name + ".tmp"
                with open(temp_name, "wb") as f:
                    f.write(file_res.content)
                
                # 교체 성공 시 기존 파일 덮어쓰기
                if os.path.exists(file_name):
                    os.remove(file_name)
                os.rename(temp_name, file_name)
                updated_count += 1
            else:
                logger.error("❌ {} 파일 다운로드 실패 (HTTP {})", file_name, file_res.status_code)
        except Exception as e:
            logger.error("❌ {} 파일 업데이트 중 에러 발생: {}", file_name, e)
            
    if updated_count > 0:
        # 5. 로컬 version.json 갱신
        try:
            with open(VERSION_FILE, "w", encoding="utf-8") as f:
                json.dump(remote_data, f, indent=2, ensure_ascii=False)
            logger.info("🎉 v{} 전략 자동 패치 업데이트 완벽 성공! (총 {}개 파일 동기화 완료)", remote_version, updated_count)
            
            # 텔레그램 알림 전송 (업데이트 성공 메시지)
            try:
                from notifier import get_notifier
                msg = (
                    f"🎉 <b>AI 스윙 봇 전략 자동 업데이트 성공</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"이전 버전: v{local_version}\n"
                    f"최신 버전: <b>v{remote_version}</b>\n"
                    f"패치 파일: 총 {updated_count}개 알고리즘 파일 동기화 완료\n"
                    f"상세 내용: 장초반 변동성 돌파 방어막 및 고급 다이내믹 탈출 엔진 연동 패치\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🤖 봇이 새로운 알고리즘으로 즉시 Hot-Reload되어 가동을 재개합니다."
                )
                get_notifier().send(msg)
            except Exception as tg_e:
                logger.debug("업데이트 완료 텔레그램 전송 실패: {}", tg_e)
                
            return True
        except Exception as e:
            logger.error("❌ 버전 정보 파일 기록 실패: {}", e)
            
    return False

if __name__ == "__main__":
    import sys
    # 로깅 포맷 가볍게 설정
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    try:
        check_and_update()
    except Exception as e:
        print("업데이트 도중 에러 발생:", e)
