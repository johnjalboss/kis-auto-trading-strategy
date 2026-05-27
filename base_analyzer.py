"""
Standard Interface for all Strategy Modules
===========================================
This ensures the master `composite_signal.py` can load any of the 70+
legacy or new modules uniformly and execute them asynchronously.
"""

from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, List, Any

class BaseAnalyzer(ABC):
    """
    All strategy/analysis modules must inherit from this class or 
    be wrapped in an Adapter that inherits from it.
    """
    
    @property
    def category(self) -> str:
        """Return the category of this analyzer (Default: TECHNICAL)"""
        return "TECHNICAL"
        
    @property
    def name(self) -> str:
        """Return the unique name of this analyzer (Default: class name)"""
        return self.__class__.__name__

    @property
    def is_symbol_dependent(self) -> bool:
        """
        Whether this analyzer depends on a specific stock symbol.
        If False, the result can be cached and reused across different stocks in the same cycle.
        Default: True
        """
        return True

    @abstractmethod
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Main execution method. Must always return a dictionary with at minimum:
        {
            'score': int (-100 to 100),
            'signals': list[str] (e.g. ["BULLISH_CROSS", "RESISTANCE_BROKEN"])
        }
        """
        pass
