"""
텔레그램 봇이 orchestrator 있는 상태에서 포지션을 올바르게 가져오는지 검증.
실제 Orchestrator를 초기화해 _get_positions_dict() 테스트.
"""
import sys, os
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

try:
    from trader import Trader
    trader = Trader()

    # orchestrator 모의 객체
    class FakeOrchestrator:
        pass

    orch = FakeOrchestrator()
    orch.trader = trader
    orch.strategy = None  # strategy 없어도 KIS API 1순위

    from telegram_interactive_bot import TelegramInteractiveBot
    bot = TelegramInteractiveBot()
    bot.orchestrator = orch

    positions = bot._get_positions_dict()
    print(f"\n✅ KIS API 포지션 ({len(positions)}개):")
    for sym, pos in positions.items():
        entry_p = getattr(pos, 'avg_price', 0.0)
        curr_p  = getattr(pos, 'current_price', entry_p)
        pnl = (curr_p - entry_p) / entry_p * 100 if entry_p > 0 else 0
        sign = "🟢" if pnl >= 0 else "🔴"
        print(f"  {sign} {sym}: {pos.quantity}주 | 평단가 ${entry_p:.2f} | 현재가 ${curr_p:.2f} ({pnl:+.2f}%)")

    if len(positions) == 5 and all(s in positions for s in ['GIS','KNSA','MDT','STRC','VTOL']):
        print("\n✅✅ 모든 5개 포지션 정상 — KIS API 우선순위 작동 확인!")
    else:
        print(f"\n⚠️  예상 5개 (GIS,KNSA,MDT,STRC,VTOL) 중 일부 누락: {list(positions.keys())}")

except Exception as e:
    import traceback
    print(f"❌ Error: {e}")
    traceback.print_exc()
