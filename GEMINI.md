# Global Workspace Rules for KIS US Stock Trading Agent

## 🌍 Multi-Timezone & Market Hours Synchronization Rule (CRITICAL)

The user frequently travels internationally, causing the local computer timestamp in `<ADDITIONAL_METADATA>` to change timezones (e.g. `+07:00` for Southeast Asia, `+09:00` for Korea/Japan, `+01:00`/`+02:00` for Europe, `-04:00`/`-05:00` for US Eastern, etc.).

### 1. Absolute Rule on Time Parsing
- **NEVER** assume the local hour in `<ADDITIONAL_METADATA>` is KST or US Eastern Time.
- **NEVER** use naive hour checks (e.g. seeing "21:xx" and assuming it is before 22:30 KST).
- **ALWAYS** parse the ISO 8601 string with its explicit offset (`±HH:MM`), convert to **UTC**, and then calculate:
  1. **US Eastern Time (ET - America/New_York)**:
     - Summer / Daylight Saving (EDT): UTC - 4 hours
     - Winter / Standard Time (EST): UTC - 5 hours
  2. **Korean Standard Time (KST - Asia/Seoul)**:
     - UTC + 9 hours
  3. **User Local Time**: The exact time in the user's current travel location.

### 2. US Stock Market Operating Hours (Anchored to US Eastern Time)
- **Pre-Market (프리마켓)**: 04:00 ~ 09:30 ET (한국 시각 17:00 ~ 22:30 KST - 서머타임 기준)
- **Regular Market (정규장 본장)**: 09:30 ~ 16:00 ET (한국 시각 22:30 ~ 05:00 KST - 서머타임 기준)
- **After-Hours (애프터마켓)**: 16:00 ~ 20:00 ET (한국 시각 05:00 ~ 09:00 KST - 서머타임 기준)
- **Closed (휴장)**: Weekends, US Holidays, or 20:00 ~ 04:00 ET

### 3. Reporting Format
Whenever answering questions about current trading status, whether a trade executed, or why no orders have been placed, ALWAYS include the 3-Way Synchronized Clock:
```markdown
🕒 [실시간 3개국 표준 시각 동기화]
• 📍 여행지 현지 시각: HH:MM (UTC±X)
• 🇰🇷 한국 기준 시각(KST): HH:MM (UTC+9)
• 🇺🇸 뉴욕 증시 현지 시각: HH:MM AM/PM EDT (정규장 진행 중 / 프리마켓 / 마감)
```
