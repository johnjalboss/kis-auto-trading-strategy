import sys
import pandas as pd
import importlib
import traceback

if __name__ == "__main__":
    print("="*70)
    print("136 Modules Full System Integrity Check")
    print("="*70)

    # 1. Load data
    import kis_data
    print("데이터 수집 엔진 가동 중...")
    df = kis_data.download('AAPL', period='90d', progress=False)
    if df is None or len(df) < 50:
        print("[FAIL] 데이터 수집 실패. API 한도를 확인하세요.")
        sys.exit(1)
    print(f"[OK] AAPL 데이터 90일치 로드 완료 (Shape: {df.shape})")

    # 2. Get all adapters
    try:
        from base_adapters import get_available_adapters
        adapters = get_available_adapters()
        print(f"\n총 {len(adapters)}개의 분석기 어댑터가 감지되었습니다. 전수 검사를 시작합니다.\n")
    except Exception as e:
        print(f"[FAIL] 어댑터 로드 실패: {e}")
        sys.exit(1)

    passed = 0
    failed = []

    for adapter_cls in adapters:
        name = adapter_cls.__name__
        try:
            inst = adapter_cls()
            res = inst.analyze(df, symbol="AAPL")
            if isinstance(res, dict) and 'score' in res:
                passed += 1
                print(f"[PASS] {name:<30} | 점수: {res['score']:>4} | 신호: {res.get('signals', [])}")
            else:
                failed.append((name, "No 'score' key in return dict"))
                print(f"[FAIL] {name:<30} | 올바르지 않은 반환값")
        except Exception as e:
            failed.append((name, f"{type(e).__name__}: {e}"))
            print(f"[FAIL] {name:<30} | {type(e).__name__}")

    print("\n" + "="*70)
    print("📊 검사 결과 요약 (SUMMARY)")
    print("="*70)
    print(f"총 검사 모듈 수 : {len(adapters)} 개")
    print(f"정상 작동 (PASS): {passed} 개")
    print(f"오류 발생 (FAIL): {len(failed)} 개")

    if failed:
        print("\n[FAIL] 오류가 발생한 모듈 목록:")
        for f_name, f_reason in failed:
            print(f" - {f_name}: {f_reason}")
    else:
        print("\n[SUCCESS] 완벽합니다! 모든 모듈이 정상적으로 데이터를 받아오고 점수를 산출합니다.")
