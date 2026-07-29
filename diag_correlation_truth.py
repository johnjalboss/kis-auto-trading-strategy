import traceback
from loguru import logger

try:
    print("Importing data_proxy...")
    import data_proxy
    print("Importing correlation_regime...")
    from correlation_regime import CorrelationRegimeDetector
    
    print("Running CorrelationRegimeDetector.analyze()...")
    detector = CorrelationRegimeDetector()
    
    # We will run the analyze code directly so we see the full traceback if it raises an exception
    # Instead of catching it inside analyze() and printing just the string, let's inspect the code
    # or print the detailed traceback since analyze() catches Exception and returns default.
    # To see the traceback of the caught exception, let's look at how analyze handles it,
    # or we can monkeypatch logger.debug to print the traceback!
    
    original_debug = logger.debug
    def debug_with_traceback(msg, *args, **kwargs):
        original_debug(msg, *args, **kwargs)
        if "Correlation analysis error" in str(msg):
            print("\n--- DETECTED CORRELATION ERROR TRACEBACK ---")
            traceback.print_exc()
            print("--------------------------------------------\n")
            
    logger.debug = debug_with_traceback
    
    regime = detector.analyze()
    print("Finished analyze. Regime:", regime.regime)
    
except Exception as e:
    print("Failed in wrapper:")
    traceback.print_exc()
