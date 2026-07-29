import sys
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')

if __name__ == "__main__":
    print('=== 가드 모듈 빠른 검증 ===')

    # 1. Earnings guard
    from earnings_calendar import get_earnings_calendar
    ec = get_earnings_calendar()
    info = ec.check('NVDA')
    print(f'NVDA 실적: {info.recommendation} (days={info.days_until})')

    # 2. Economic calendar
    from economic_calendar import get_economic_calendar
    econ = get_economic_calendar()
    events = econ.get_todays_events()
    print(f'오늘 경제지표: {[e.name for e in events]}')
    safe, reason = econ.is_safe_to_trade()
    print(f'매매 안전: {safe} ({reason})')

    # 3. strategy.py import
    print('strategy.py 임포트...', end=' ', flush=True)
    import strategy
    print('OK')

    print('ALL OK - 모든 가드 정상 동작')

