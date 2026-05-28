"""
Universal Adapters for 130+ Modules
====================================
Auto-discovers ALL Python modules in the project, wraps their classes
into the standardized `BaseAnalyzer` interface for `composite_signal.py`.

Discovery Strategy:
1. Hard-coded adapters for core modules with specific wiring
2. Auto-imports every .py file not in BLACKLIST
3. Wraps classes that have ANY callable analysis method
4. Categorizes by filename heuristic
"""

from base_analyzer import BaseAnalyzer
from loguru import logger
import pandas as pd
import numpy as np
from typing import Dict, Any, List
import os
import importlib
import inspect

# =====================================================================
# Methods that qualify a class as "analyzable"
# Strictly restricted to non-mutating, diagnostic methods
# =====================================================================
ANALYSIS_METHODS = {
    'analyze', 'detect', 'check', 'evaluate', 'predict', 'scan',
    'full_scan', 'calculate', 'generate', 'get_score', 'get_opportunity_score',
    'calculate_macro_score', 'filter_macro_headwinds', 'check_today',
    'is_trade_worth_it', 'scan_watchlist', 'is_safe_to_trade',
    'quick_check', 'calculate_position_size', 'get_stats', 'get_recent',
    'calculate_entry_cost', 'get_hedge_positions', 'get_drawdown'
}

# Files to skip (infrastructure or scripts, not signal modules)
BLACKLIST_PATTERNS = [
    'main', 'test_', 'backtest', 'deploy', 'orchestrator', 
    'kis_', 'read_', 'extract_', 'verify', 'dashboard', 
    'Start_', '__', 'check_', 'diag_', 'integration_test',
    'base_adapters', 'base_analyzer', 'config', 'audit_',
    'ai_judge', 'all_modules_', 'competition_mode', 'reporter',
    'test', 'count_adapters', 'deep_verify', 'inspect_', 'alpha_',
    'trader', 'strategy', 'screener', 'risk_manager', 'database',
    'data_proxy', 'auth', 'keepalive', 'health_monitor', 'watchdog',
    'scheduler', 'notification', 'notifier', 'smart_order', 'indicators',
    'utils', 'trade', 'composite_signal', 'signal_aggregator',
    'frequency_controller', 'server_', 'fix_', 'debug_', 'temp_',
    'troubleshoot', 'diag_', 'capture_', 'parsed_', 'decoded_', 
    'generate_', 'fetch_', 'local_', 'remote_', 'setup_', 'run_',
    'CandlePattern', 'CandlestickSignal', 'ultimate_strategy',
    # New additions to prevent side-effects
    'drawdown_recovery', 'emergency_stop', 'performance_audit', 
    'winrate_optimizer', 'trade_journal', 'portfolio_manager',
    'execution_tracker', 'risk_controller',
    # Day trading logic to be excluded from Swing engine
    'intraday_momentum', 'premarket_gap',
    # Utilities with potential global import side-effects
    'clean', 'get_logs', 'run_remote', 'sell', 'analyze_', 'backfill_', 'reset_', 'try_',
    'simple_audit', 'deep_audit', 'clean_stale'
]

# Modules that are pure infrastructure — loaded by orchestrator, never signal adapters
INFRASTRUCTURE_MODULES = {
    'auth', 'trader', 'strategy', 'screener', 'risk_manager',
    'database', 'data_proxy', 'keepalive', 'health_monitor', 'watchdog',
    'scheduler', 'notification', 'notifier', 'smart_order', 'indicators',
    'utils', 'trade', 'composite_signal', 'signal_aggregator',
    'frequency_controller',  # Orchestrator-only (timing gate)
}

# =====================================================================
# Category detection by filename heuristic
# =====================================================================
def _guess_category(filename: str) -> str:
    f = filename.lower()
    if any(k in f for k in ['macro', 'geo', 'fed', 'oil', 'yen', 'global', 'economic']):
        return "MACRO"
    if any(k in f for k in ['flow', 'smart_money', 'option', 'insider', 'credit', 'order_flow']):
        return "SMART_MONEY"
    if any(k in f for k in ['fund', 'earn', 'valuation']):
        return "FUNDAMENTAL"
    if any(k in f for k in ['senti', 'psycho', 'social', 'news', 'crypto_sent']):
        return "SENTIMENT"
    if any(k in f for k in ['risk', 'hedge', 'stress', 'drawdown', 'emergency', 'stop', 'anti_frag', 'tail']):
        return "RISK"
    if any(k in f for k in ['regime', 'breadth', 'sector', 'rotation', 'intermarket', 'correlation', 'vix']):
        return "MACRO"
    if any(k in f for k in ['ml_', 'predict', 'monte', 'stat_arb', 'hidden_markov']):
        return "QUANTITATIVE"
    if any(k in f for k in ['exec', 'exit', 'frequency', 'manipulation', 'realtime', 'gap_scan', 'premarket']):
        return "EXECUTION"
    if any(k in f for k in ['perf', 'winrate', 'attribution', 'diagnosis', 'journal', 'report', 'alpha']):
        return "PERFORMANCE"
    if any(k in f for k in ['compound', 'scaling', 'portfolio', 'kelly', 'position', 'cost', 'tax']):
        return "SIZING"
    return "TECHNICAL"


# =====================================================================
# Universal Adapter — wraps arbitrary classes
# =====================================================================
class UniversalAdapter(BaseAnalyzer):
    """Dynamically wraps ANY module class into the BaseAnalyzer interface"""
    
    def __init__(self, target_class, category="TECHNICAL", method_name="analyze"):
        self._target_class = target_class
        self._category = category
        self._method_name = method_name
        self._instance = None  # Lazy init
        
    def _get_instance(self):
        if self._instance is None:
            try:
                self._instance = self._target_class()
            except Exception:
                # Some classes need args — try common patterns
                try:
                    self._instance = self._target_class(initial_capital=10000)
                except Exception:
                    try:
                        self._instance = self._target_class(data_file="default.json")
                    except Exception:
                        self._instance = None
        return self._instance
        
    @property
    def category(self) -> str: 
        return self._category
    
    @property
    def is_symbol_dependent(self) -> bool:
        # MACRO and GLOBAL signals typically don't depend on the current symbol
        return self._category.upper() not in ["MACRO", "GLOBAL"]

    @property
    def name(self) -> str: 
        return self._target_class.__name__
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        result = {'score': 0, 'signals': [], 'source': self.name}
        
        instance = self._get_instance()
        if instance is None:
            return result
            
        try:
            method = getattr(instance, self._method_name, None)
            if method is None:
                return result
            
            # Check what the method actually expects
            sig = inspect.signature(method)
            params = sig.parameters
            param_names = list(params.keys())
            
            # Try calling intelligently based on signature
            output = None
            
            # Identify which parameter wants the symbol
            sym_params = ['symbol', 'ticker', 'target_symbol', 'target']
            sym_param_name = next((p for p in param_names if p in sym_params), None)
            
            # Special case for 'update' method (e.g. TrailingStopManager) which often needs price
            price_val = kwargs.get('price') or kwargs.get('current_price')
            if price_val is None and df is not None and not df.empty:
                try:
                    price_val = float(df['Close'].iloc[-1])
                except: pass
            
            if sym_param_name:
                sym = kwargs.get('symbol') or kwargs.get('ticker')
                if not sym:
                    # If df is provided and it's a string (unlikely but possible if misconfigured), use it
                    if isinstance(df, str):
                        sym = df
                    else:
                        return result  # Cannot run without symbol
                
                try:
                    call_args = {sym_param_name: sym}
                    if 'df' in params: call_args['df'] = df
                    if 'data' in params: call_args['data'] = df
                    if 'current_price' in params: call_args['current_price'] = price_val
                    if 'price' in params: call_args['price'] = price_val
                    
                    # Call with collected args
                    output = method(**call_args)
                except Exception as e:
                    logger.debug(f"Error calling {self.name}.{self._method_name} with symbol: {e}")
            else:
                # Provide price if expected
                call_args = {}
                if 'df' in params: call_args['df'] = df
                if 'data' in params: call_args['data'] = df
                if 'current_price' in params: call_args['current_price'] = price_val
                if 'price' in params: call_args['price'] = price_val
                
                # If the method expects a specific parameter like 'new_capital', and we have capital in kwargs, use it
                if 'new_capital' in params and 'capital' in kwargs:
                    call_args['new_capital'] = kwargs['capital']
                
                if call_args:
                    output = method(**call_args)
                else:
                    # Generic call fallback
                    try:
                        # Only pass df if it seems like it wants it (has positional param or generic **kwargs)
                        if any(p.kind in [p.POSITIONAL_OR_KEYWORD, p.POSITIONAL_ONLY] for p in params.values()):
                            output = method(df, **kwargs)
                        else:
                            output = method(**kwargs)
                    except TypeError:
                        try:
                            output = method(df)
                        except TypeError:
                            try:
                                output = method()
                            except Exception:
                                pass
            
            # Extract score from output
            result = self._extract_score(output, result)
            
        except Exception as e:
            logger.debug("Adapter {} error: {}", self.name, str(e)[:80])
        
        return result
    
    def _extract_score(self, output, result: dict) -> dict:
        """Extract a usable score from various output formats"""
        if output is None:
            return result
            
        # Avoid DataFrame ambiguity errors
        if isinstance(output, pd.DataFrame):
            if output.empty:
                return result
            # Try to get something useful if it's a small DF, otherwise neutral
            if len(output) == 1:
                try:
                    result['score'] = int(output.iloc[0].get('score', 0))
                except: pass
            return result

        # Dict output
        if isinstance(output, dict):
            try:
                result['score'] = output.get('score', output.get('risk_score', 0))
                if 'signals' in output:
                    result['signals'].extend([str(s) for s in output['signals']])
                if output.get('is_squeezing'):
                    result['score'] = 20
                    result['signals'].append(f"{self.name}_SQUEEZE")
                if output.get('regime'):
                    result['signals'].append(f"REGIME_{output['regime']}")
                # Negative score for high risk
                if 'risk_score' in output and output['risk_score'] > 50:
                    result['score'] = -output['risk_score'] // 2
            except (ValueError, TypeError):
                pass
            return result
        
        # Numeric output
        if isinstance(output, (int, float, np.integer, np.floating)):
            result['score'] = int(output)
            return result
        
        # Boolean output (common for should_* methods)
        if isinstance(output, bool) or isinstance(output, np.bool_):
            result['score'] = 10 if bool(output) else -10
            result['signals'].append(f"{self.name}_{'TRUE' if output else 'FALSE'}")
            return result
        
        # Object with attributes
        if hasattr(output, '__dict__') or hasattr(output, '__dataclass_fields__'):
            for attr in ['score', 'bonus_score', 'risk_score', 'signal_score', 'overall_score', 'credit_score', 'vix_score']:
                if hasattr(output, attr):
                    val = getattr(output, attr) 
                    # Fix DataFrame ambiguity for custom objects
                    if isinstance(val, (int, float, np.integer, np.floating)):
                        result['score'] = int(val)
                        break
                    try:
                        # Handle potential numpy types or single-value objects
                        if not isinstance(val, (pd.DataFrame, pd.Series, list, dict)):
                            result['score'] = int(float(val))
                            break
                    except: pass
            
            for attr in ['details', 'signals', 'description', 'summary', 'recommendation']:
                if hasattr(output, attr):
                    val = getattr(output, attr)
                    if isinstance(val, list):
                        result['signals'].extend([str(s) for s in val[:3]])
                    elif isinstance(val, str) and val:
                        result['signals'].append(val[:60])
                    break
        
        # List output
        if isinstance(output, (list, tuple)) and len(output) > 0:
            result['signals'].append(f"{self.name}_{len(output)}_items")
            result['score'] = min(len(output), 15)
        
        return result


# =====================================================================
# Discovery Engine
# =====================================================================
_cache = None

def _discover_adapters() -> List:
    """Scan all .py files and auto-wrap discoverable classes"""
    global _cache
    if _cache is not None:
        return _cache
    
    discovered = []
    loaded_names = set()
    failed_modules = []
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    py_files = sorted([f for f in os.listdir(current_dir) 
                       if f.endswith('.py') and not any(b in f for b in BLACKLIST_PATTERNS)])
    
    for filename in py_files:
        mod_name = filename[:-3]
        
        # Skip infrastructure modules 
        if mod_name in INFRASTRUCTURE_MODULES:
            continue
        
        try:
            module = importlib.import_module(mod_name)
        except Exception as e:
            failed_modules.append((mod_name, str(e)[:60]))
            continue
        
        category = _guess_category(filename)
        
        for class_name, cls in inspect.getmembers(module, inspect.isclass):
            # Only classes defined in this module
            if cls.__module__ != mod_name:
                continue
            
            # Suffix check: Skip managers, traders, auditors, journals (higher risk of side-effects)
            # Allow analytical 'tracker' classes (e.g. SmartMoneyTracker, ETFFlowTracker, InsiderInstitutionalTracker)
            if any(s in class_name.lower() for s in ['manager', 'trader', 'auditor', 'journal']):
                continue

            if class_name == 'BaseAnalyzer' or any(p in class_name for p in BLACKLIST_PATTERNS):
                continue
            
            # Already a BaseAnalyzer subclass — add directly
            if issubclass(cls, BaseAnalyzer):
                if class_name not in loaded_names:
                    discovered.append(cls)
                    loaded_names.add(class_name)
                continue
            
            # Find the best analysis method
            best_method = None
            for method_name in ANALYSIS_METHODS:
                if hasattr(cls, method_name) and callable(getattr(cls, method_name, None)):
                    best_method = method_name
                    break
            
            if best_method and class_name not in loaded_names:
                # Create an adapter instance
                adapter = UniversalAdapter(cls, category, best_method)
                
                # Define a concrete subclass of BaseAnalyzer to wrap this adapter
                class AdapterWrapper(BaseAnalyzer):
                    _adapter_instance = adapter
                    
                    @property
                    def category(self) -> str:
                        return self._adapter_instance.category
                        
                    @property
                    def name(self) -> str:
                        return self._adapter_instance.name
                        
                    @property
                    def is_symbol_dependent(self) -> bool:
                        return self._adapter_instance.is_symbol_dependent
                        
                    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
                        return self._adapter_instance.analyze(df, **kwargs)
                
                # Set a recognizable name for debugging
                AdapterWrapper.__name__ = f"{class_name}Adapter"
                
                discovered.append(AdapterWrapper)
                loaded_names.add(class_name)
    
    # Log results
    logger.info("Auto-Discovery: {} adapters loaded, {} modules failed", 
                len(discovered), len(failed_modules))
    for mod_name, err in failed_modules:
        logger.warning("  Module {} failed: {}", mod_name, err)
    
    _cache = discovered
    return discovered


def get_available_adapters() -> List:
    """Return all discovered adapter classes"""
    return _discover_adapters()


def get_adapter_report() -> Dict[str, Any]:
    """Get detailed report of what was discovered"""
    adapters = get_available_adapters()
    by_category = {}
    for a in adapters:
        try:
            inst = a() if inspect.isclass(a) else a
            cat = inst.category if hasattr(inst, 'category') else "UNKNOWN"
            name = inst.name if hasattr(inst, 'name') else str(a)
            by_category.setdefault(cat, []).append(name)
        except Exception:
            pass
    return {
        'total': len(adapters),
        'by_category': by_category,
    }
