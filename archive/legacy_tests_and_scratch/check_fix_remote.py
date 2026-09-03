from trader import ExchangeMapper, get_trader
import os

print(f"Mapping in ExchangeMapper: {ExchangeMapper.get_exchange('PLTD')}")

trader = get_trader()
for exch in ["NASD", "NYS", "AMS", "NAS", "NYS", "AMS"]:
    print(f"\nChecking exchange: {exch}")
    try:
        # We use a custom call to check positions for THIS exchange only
        # This depends on how get_positions is implemented in your trader.py
        # If get_positions doesn't take an exchange, we might need to check the KIS API directly.
        pass
    except Exception as e:
        print(f"Error checking {exch}: {e}")

# Let's check the env to make sure it's the right account
print(f"KIS_CANO: {os.getenv('KIS_CANO')}")
