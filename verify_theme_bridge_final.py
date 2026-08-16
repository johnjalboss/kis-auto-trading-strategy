from theme_radar_adapter import ThemeRadarAdapter

adapter = ThemeRadarAdapter()
true_sigs = adapter.get_true_signals()
recs = adapter.get_recommendations()

print(f"=== THEME RADAR 24/7 REAL-TIME BRIDGE ACTIVE ===")
print(f"Total True Signals (🟢 진짜 주도 테마): {len(true_sigs)}")
for s in true_sigs[:5]:
    print(f"  [{s['theme_id']}] {s['name_ko']} (Quality: {s['quality']}, RVOL: {s['med_rvol']}x, 5D Ret: {s['ret_5d']}%)")

print(f"\nTotal Leader/Setup Stock Recommendations: {len(recs)}")
top_recs = list(recs.items())[:8]
for ticker, info in top_recs:
    print(f"  {ticker:6s} | Type: {info['pick_type']:6s} | Price: ${info['price']:<7.2f} | Target: ${info['target_price']:<7.2f} (+{info['target_pct']}%) | Stop: ${info['stop_loss']:<7.2f} (-{info['stop_pct']}%) | Theme: {info['theme_name']}")
