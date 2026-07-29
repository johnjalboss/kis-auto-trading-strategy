#!/usr/bin/env python3
"""orchestrator.py 의 auto_tuner 섹션을 수동으로 올바르게 수정"""

path = '/home/ubuntu/kis-auto-trading/orchestrator.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 문제 구간 찾기: '# 6. Auto Tuner' 부터 'self._safe_import("auto_tuner"' 까지
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if '# 6. Auto Tuner' in line and start_idx is None:
        start_idx = i
    if 'self._safe_import("auto_tuner"' in line and start_idx is not None:
        end_idx = i
        break

if start_idx is None or end_idx is None:
    print(f"[ERROR] 구간을 찾지 못했습니다: start={start_idx}, end={end_idx}")
    # 수동으로 직접 찾기
    for i, line in enumerate(lines):
        if 'auto_tuner' in line.lower():
            print(f"  Line {i+1}: {line.rstrip()}")
else:
    print(f"[INFO] 수정 구간: lines {start_idx+1}~{end_idx+1}")
    print("[BEFORE]")
    for l in lines[start_idx:end_idx+1]:
        print(f"  {l.rstrip()}")

    # 올바른 내용으로 교체
    fixed_block = '''\
        # 6. Auto Tuner + 학습 리포트 (매일 실행)
        def _tuner():
            from auto_tuner_new import run_auto_tune
            threading.Thread(target=run_auto_tune, daemon=True, name="AutoTuner").start()
            logger.info("  -> auto_tuner_new.py: AI 학습 리포트 스레드 시작")
        self._safe_import("auto_tuner", _tuner)
'''
    lines[start_idx:end_idx+1] = [fixed_block]
    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("[FIXED] 올바른 auto_tuner 섹션으로 교체 완료")

# 문법 검사
import py_compile, sys
try:
    py_compile.compile(path, doraise=True)
    print("[OK] orchestrator.py 문법 검사 통과")
except py_compile.PyCompileError as e:
    print(f"[SYNTAX ERROR] {e}")
    sys.exit(1)
