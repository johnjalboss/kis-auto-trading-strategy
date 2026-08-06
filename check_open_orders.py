from trader import get_trader
import os

def check():
    try:
        t = get_trader()
        orders = t.get_unfilled_orders()
        if not orders:
            print("No unfilled orders found.")
        else:
            for o in orders:
                # Assuming o has symbol, quantity, order_no, exchange attributes
                # Adjusting based on common OrderResult or similar structures in the bot
                symbol = getattr(o, 'symbol', 'Unknown')
                qty = getattr(o, 'quantity', '0')
                ono = getattr(o, 'order_no', 'N/A')
                exch = getattr(o, 'exchange', 'N/A')
                print(f"OPEN ORDER: {symbol} | Qty: {qty} | OrderNo: {ono} | Exch: {exch}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check()
