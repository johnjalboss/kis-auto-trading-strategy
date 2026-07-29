import sys
import unittest.mock
sys.modules['system_setup'] = unittest.mock.Mock()

import data_proxy
from loguru import logger

if __name__ == "__main__":
    logger.add(sys.stderr, level="DEBUG")
    
    from composite_signal import get_composite_engine
    print("Running engines...")
    engine = get_composite_engine()
    engine.analyze("AAPL")
    print("Done")
