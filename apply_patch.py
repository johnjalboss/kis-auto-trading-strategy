#!/usr/bin/env python3
"""
서버 상의 3개 파일을 직접 수정하는 패치 스크립트:
1. orchestrator.py - self.risk_manager → self.rm 수정 + auto_tuner → auto_tuner_new 수정
2. strategy.py     - CHOPPY 레짐 진입 차단 추가
"""
import re

# ===================================================
# 1. orchestrator.py 패치
# ===================================================
path = '/home/ubuntu/kis-auto-trading/orchestrator.py'
with open(path, 'r', encoding='utf-8') as f:
    txt = f.read()

# 1-A: self.risk_manager → self.rm (circuit breaker 버그)
old = "getattr(self.risk_manager, 'day_start_equity', total_equity)"
new = "getattr(self.rm, 'day_start_equity', total_equity) if hasattr(self, 'rm') else total_equity"
if old in txt:
    txt = txt.replace(old, new)
    print("[FIXED] orchestrator.py: self.risk_manager → self.rm")
else:
    print("[SKIP]  orchestrator.py: risk_manager pattern not found")

# 1-B: auto_tuner → auto_tuner_new (학습 리포트 발송)
old_tuner = "from auto_tuner import run_auto_tune"
new_tuner = "from auto_tuner_new import run_auto_tune"
if old_tuner in txt:
    txt = txt.replace(old_tuner, new_tuner)
    print("[FIXED] orchestrator.py: auto_tuner → auto_tuner_new")
else:
    print("[SKIP]  orchestrator.py: auto_tuner pattern not found (may already be fixed)")

# 1-C: 일요일만 → 매일 실행 (학습 리포트 매일 발송)
old_sunday = """    if now.weekday() == 6:
                threading.Thread(target=run_auto_tune, daemon=True, name="AutoTuner").start()
                logger.info("  -> auto_tuner.py:     ()")
            else:
                logger.info("  -> auto_tuner.py:    ( ,  {})",
                            ['','','','','','',''][now.weekday()])"""
new_daily = """    # 매일 실행 (학습 리포트 + 파라미터 최적화)
                threading.Thread(target=run_auto_tune, daemon=True, name="AutoTuner").start()
                logger.info("  -> auto_tuner_new.py: AI 학습 스레드 시작")"""

if "now.weekday() == 6" in txt and "AutoTuner" in txt:
    # 더 안전한 패턴으로 교체
    txt = re.sub(
        r'if now\.weekday\(\) == 6:\s*\n\s*threading\.Thread\(target=run_auto_tune.*?AutoTuner.*?\)\.start\(\)\s*\n\s*logger\.info\(.*?auto_tuner.*?\)\s*\n\s*else:\s*\n\s*logger\.info\(.*?auto_tuner.*?\n.*?\)',
        '# 매일 실행\n                threading.Thread(target=run_auto_tune, daemon=True, name="AutoTuner").start()\n                logger.info("  -> auto_tuner_new.py: AI 학습 리포트 스레드 시작")',
        txt,
        flags=re.DOTALL
    )
    print("[FIXED] orchestrator.py: auto_tuner 일요일→매일 실행")
else:
    print("[SKIP]  orchestrator.py: weekday pattern not found")

with open(path, 'w', encoding='utf-8') as f:
    f.write(txt)
print(f"[SAVED] {path}")

# ===================================================
# 2. strategy.py 패치 - CHOPPY 레짐 진입 차단
# ===================================================
path2 = '/home/ubuntu/kis-auto-trading/strategy.py'
with open(path2, 'r', encoding='utf-8') as f:
    txt2 = f.read()

old_bear = '''        _bear_regimes = {"BEAR_NORMAL", "BEAR_TRENDING", "BEAR_VOLATILE"}
        current_regime = getattr(self, '_last_regime', '')
        if current_regime in _bear_regimes:
            _allowed_in_bear = getattr(config, 'INVERSE_ETFS', set()) | getattr(config, 'DEFENSIVE_UNIVERSE_SET', set())
            if symbol not in _allowed_in_bear:
                return EntrySignal("HOLD", 0, f"BEAR_REGIME_BLOCK: {current_regime}  only inverse/defensive allowed", 0)'''

new_bear = '''        _bear_regimes = {"BEAR_NORMAL", "BEAR_TRENDING", "BEAR_VOLATILE"}
        _choppy_regimes = {"CHOPPY", "TRANSITION", "CHOPPY_VOLATILE"}
        current_regime = getattr(self, '_last_regime', '')

        # CHOPPY/TRANSITION 레짐: 방향성이 없어 승률 저하 → 진입 차단
        if current_regime in _choppy_regimes:
            logger.debug("CHOPPY_REGIME_BLOCK: {} — {} 레짐에서 신규 진입 차단", symbol, current_regime)
            return EntrySignal("HOLD", 0, f"CHOPPY_REGIME_BLOCK: {current_regime} — 방향성 없음", 0)

        if current_regime in _bear_regimes:
            _allowed_in_bear = getattr(config, 'INVERSE_ETFS', set()) | getattr(config, 'DEFENSIVE_UNIVERSE_SET', set())
            if symbol not in _allowed_in_bear:
                return EntrySignal("HOLD", 0, f"BEAR_REGIME_BLOCK: {current_regime}  only inverse/defensive allowed", 0)'''

if '_bear_regimes' in txt2 and '_choppy_regimes' not in txt2:
    txt2 = txt2.replace(old_bear, new_bear)
    print("[FIXED] strategy.py: CHOPPY 레짐 진입 차단 추가")
elif '_choppy_regimes' in txt2:
    print("[SKIP]  strategy.py: CHOPPY block already exists")
else:
    print("[WARN]  strategy.py: bear_regimes pattern not found exactly — manual check needed")

with open(path2, 'w', encoding='utf-8') as f:
    f.write(txt2)
print(f"[SAVED] {path2}")

print("\n=== 패치 완료 ===")
