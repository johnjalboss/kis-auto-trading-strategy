from trader import get_trader
import os
import time

def manual_sell():
    print("Initiating manual sell for PLTD...")
    try:
        t = get_trader()
        # Verify current mapping
        from trader import ExchangeMapper
        mapper = ExchangeMapper()
        print(f"Current mapping for PLTD: {mapper.get_exchange('PLTD')}")
        
        # Execute sell with current price
        price = t.get_price('PLTD')
        print(f"Current price for PLTD: {price}")
        res = t.sell('PLTD', 1, limit_price=price)
        print(f"Order Result: {res}")
        
        if getattr(res, 'success', False):
            print("Successfully placed sell order for PLTD.")
        else:
            print(f"Failed to place sell order: {res.reason}")
            
    except Exception as e:
        print(f"Error during manual sell: {e}")

if __name__ == "__main__":
    manual_sell()
