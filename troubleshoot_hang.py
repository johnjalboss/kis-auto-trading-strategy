import sys
print("STEP 1: Starting import of base_adapters")
try:
    import base_adapters
    print("STEP 2: Successfully imported base_adapters")
except Exception as e:
    print(f"FAILED IMPORT: {e}")
    sys.exit(1)

print("STEP 3: Calling get_available_adapters()")
try:
    adapters = base_adapters.get_available_adapters()
    print(f"STEP 4: SUCCESS! Got {len(adapters)} adapters")
except Exception as e:
    print(f"FAILED GETTING ADAPTERS: {e}")
