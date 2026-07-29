"""캐시 삭제 후 유니버스 강제 갱신 & 결과 확인"""
import os, json
from pathlib import Path

if __name__ == "__main__":
    # 1) 캐시 삭제
    cache = Path('universe_cache.json')
    if cache.exists():
        cache.unlink()
        print("Old cache deleted")

    # 2) 강제 재로딩
    import universe
    universe._universe_cache = None
    syms = universe.get_all_symbols()

    # 3) 결과 출력
    print(f"\n=== UNIVERSE SIZE: {len(syms)} ===")
    print(f"First 20 : {syms[:20]}")
    print(f"Last  10 : {syms[-10:]}")

    # 새 캐시 확인
    if cache.exists():
        d = json.loads(cache.read_text())
        print(f"\nCache saved: {d['count']} symbols @ {d['updated']}")
