# Global Workspace Rules for KIS US Stock Trading Agent

## 🌍 1. Multi-Timezone & Market Hours Synchronization Rule (CRITICAL)

The user frequently travels internationally, causing the local computer timestamp in `<ADDITIONAL_METADATA>` to change timezones (e.g. `+07:00` for Southeast Asia, `+09:00` for Korea/Japan, `+01:00`/`+02:00` for Europe, `-04:00`/`-05:00` for US Eastern, etc.).

### Absolute Rule on Time Parsing
- **NEVER** assume the local hour in `<ADDITIONAL_METADATA>` is KST or US Eastern Time.
- **NEVER** use naive hour checks (e.g. seeing "21:xx" and assuming it is before 22:30 KST).
- **ALWAYS** parse the ISO 8601 string with its explicit offset (`±HH:MM`), convert to **UTC**, and then calculate:
  1. **US Eastern Time (ET - America/New_York)**:
     - Summer / Daylight Saving (EDT): UTC - 4 hours
     - Winter / Standard Time (EST): UTC - 5 hours
  2. **Korean Standard Time (KST - Asia/Seoul)**:
     - UTC + 9 hours
  3. **User Local Time**: The exact time in the user's current travel location.

### US Stock Market Operating Hours (Anchored to US Eastern Time)
- **Pre-Market (프리마켓)**: 04:00 ~ 09:30 ET (한국 시각 17:00 ~ 22:30 KST - 서머타임 기준)
- **Regular Market (정규장 본장)**: 09:30 ~ 16:00 ET (한국 시각 22:30 ~ 05:00 KST - 서머타임 기준)
- **After-Hours (애프터마켓)**: 16:00 ~ 20:00 ET (한국 시각 05:00 ~ 09:00 KST - 서머타임 기준)
- **Closed (휴장)**: Weekends, US Holidays, or 20:00 ~ 04:00 ET

### Reporting Format
Whenever answering questions about current trading status, whether a trade executed, or why no orders have been placed, ALWAYS include the 3-Way Synchronized Clock:
```markdown
🕒 [실시간 3개국 표준 시각 동기화]
• 📍 여행지 현지 시각: HH:MM (UTC±X)
• 🇰🇷 한국 기준 시각(KST): HH:MM (UTC+9)
• 🇺🇸 뉴욕 증시 현지 시각: HH:MM AM/PM EDT (정규장 진행 중 / 프리마켓 / 마감)
```

---

## 🚀 2. Dual-Deployment Protocol (Oracle VPS & GitHub Mandatory Sync)

**절대 원칙**: 모든 코드 수정, 버그 수정, 퀀트 엔진 튜닝, UI 개선 작업은 **수정 즉시 예외 없이 오라클 VPS와 지인 배포용 깃허브(GitHub) 두 곳 모두에 완전 동시 배포**해야 한다. 사용자에게 재차 지시받기 전에 매 작업마다 자동으로 일괄 완료해야 한다.

### 필수 실행 절차 (Every Modification):
1. **로컬 패키지 동기화**: `kis-auto-trading/`의 모든 변경 파일을 `kis-auto-trading-packaged/`로 즉시 동기화.
2. **지인 배포용 깃허브 커밋 & 푸시**:
   - 위치: `C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading-packaged`
   - `git add <수정파일>`
   - `git commit -m "명확한 변경 내역 요약"`
   - `git push origin main`
3. **오라클 클라우드 VPS 실서버 배포**:
   - SFTP로 `/home/ubuntu/kis-auto-trading/` 경로에 동일 파일 업로드.
   - 수정 파일에 따라 관련 데몬 서비스 재시작 (`sudo systemctl restart telegram-interactive.service` 또는 `kis-trading.service`).
   - 서비스 정상 작동 상태(`systemctl is-active`) 확인.
4. **결과 보고**: 답변 시 오라클 VPS 적용 상태와 깃허브 최신 커밋 해시를 항상 함께 명시할 것.
