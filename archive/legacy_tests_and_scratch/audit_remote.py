
import strategy
print("Strategy members:")
for x in dir(strategy):
    if not x.startswith("__"):
        print(f"  {x}")
