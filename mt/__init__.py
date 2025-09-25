"""
MT5 Trading System

MetaTrader5 integration for automated trading based on LLM signals.
"""

from .config.settings import get_mt5_settings, validate_settings
from .logger import setup_logging, get_logger

# Import MT5-dependent modules conditionally
try:
    from .core.connection import MT5Connection
    from .core.trader import MT5Trader, TradeResult, TradeExecution
    MT5_MODULES_AVAILABLE = True
except ImportError:
    # Create dummy classes when MT5 is not available
    MT5Connection = None
    MT5Trader = None
    TradeResult = None
    TradeExecution = None
    MT5_MODULES_AVAILABLE = False

try:
    from .core.llm_client import LLMClient
except ImportError:
    LLMClient = None

__version__ = "1.0.0"
__author__ = "MT5 Trading System"

__all__ = [
    "get_mt5_settings",
    "validate_settings", 
    "MT5Connection",
    "MT5Trader",
    "TradeResult", 
    "TradeExecution",
    "LLMClient",
    "setup_logging",
    "get_logger",
    "MT5_MODULES_AVAILABLE"
]
