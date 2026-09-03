from theme_radar_adapter import ThemeRadarAdapter
import os

tra = ThemeRadarAdapter()
print("DB Path:", tra.db_path)
print("DB Exists:", os.path.exists(tra.db_path))

true_sigs = tra.get_true_signals()
print(f"\n=== TRUE SIGNALS ({len(true_sigs)}) ===")
for s in true_sigs:
    print(s)

recs = tra.get_recommendations()
print(f"\n=== THEME RECOMMENDATIONS ({len(recs)}) ===")
for k, v in recs.items():
    print(f"  {k:6s}: {v}")
