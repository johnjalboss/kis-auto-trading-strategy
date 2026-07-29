from trader import get_trader, OrderResult
import os

def manual_sell():
    print("Initiating robust manual sell for PLTD...")
    try:
        t = get_trader()
        
        # 1. Get current price
        price = t.get_price('PLTD')
        print(f"Fetched price for PLTD: {price}")
        
        if price <= 0:
            print("Price fetch returned 0. Using fallback price 7.28.")
            price = 7.28
            
        # 2. Execute sell (NYSE mapping is already in trader.py on server)
        res = t.sell('PLTD', 1, limit_price=price)
        print(f"Order Execution Attempted.")
        print(f"Success: {res.success}")
        print(f"Message: {res.message}")
        print(f"Order ID: {res.order_id}")
        
        if res.success:
            print("SUCCESS: Sell order placed successfully.")
        else:
            print(f"FAILURE: {res.message}")
            
    except Exception as e:
        print(f"Error during robust manual sell: {e}")

if __name__ == "__main__":
    manual_sell()
