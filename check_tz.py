from datetime import datetime
import pytz

et = pytz.timezone('US/Eastern')
kst = pytz.timezone('Asia/Seoul')
now_et = datetime.now(et)
now_kst = datetime.now(kst)

print(f"KST: {now_kst.strftime('%Y-%m-%d %H:%M')}")
print(f"ET:  {now_et.strftime('%Y-%m-%d %H:%M')}")
print()
print(f"KST date: {now_kst.date()}")
print(f"ET  date: {now_et.date()}")
print()

# Check economic calendar with ET date (correct)
from economic_calendar import EconomicCalendar
ec = EconomicCalendar()
print("=== FOMC 스케줄 전체 ===")
for ev in ec.events_cache:
    if ev.name == "FOMC":
        print(f"  FOMC: {ev.date.strftime('%Y-%m-%d')}")

print()
print("현재 KST date로 체크하면:", [e.name for e in ec.get_todays_events()])
print("현재 ET date 기준으로 체크하면:")
today_et = now_et.date()
et_events = [e for e in ec.events_cache if e.date.date() == today_et]
print(" ", [e.name for e in et_events] if et_events else "없음")
