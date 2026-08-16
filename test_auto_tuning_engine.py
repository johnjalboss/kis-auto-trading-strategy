"""
Unit test for auto_tuning_engine.py
"""
import sys, os, json
from auto_tuning_engine import AutoTuningEngine

print("==========================================================")
print("[TEST] INSTITUTIONAL AUTO-TUNING ENGINE")
print("==========================================================")

tuner = AutoTuningEngine()
metrics = tuner.analyze_performance()
print("1. Performance Metrics Analysis:", metrics)

res = tuner.run_autotune()
print("\n2. AutoTuning Optimization Result:")
print(json.dumps(res, indent=2, ensure_ascii=False))

print("==========================================================")
