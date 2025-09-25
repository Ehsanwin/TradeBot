"""
LLM Trading Analysis System

A comprehensive AI-powered forex trading analysis system that uses ChatGPT to:
- Fetch and normalize market data from forex, technical analysis, and news sources
- Generate intelligent trading signals (buy/sell/hold decisions)
- Analyze market news and economic events impact
- Create detailed market reports with actionable insights

Key Components:
- Market Data Service: Fetches data from TradeBot APIs
- Signal Generator: Uses ChatGPT for trading signal analysis
- Market Reporter: Creates comprehensive market analysis reports
- Configuration: Flexible settings management with environment variables

Usage:
    from LLM.main import LLMTradingSystem
    
    system = LLMTradingSystem()
    system.initialize_services()
    results = system.run_analysis()
    system.print_results(results)
"""

__version__ = "1.0.0"
__author__ = "Trading Bot System"

from .main import LLMTradingSystem
from .config.settings import get_llm_settings
from .core.data_types import (
    TradingSignal, MarketReport, SignalType, SignalStrength
)

__all__ = [
    "LLMTradingSystem",
    "get_llm_settings", 
    "TradingSignal",
    "MarketReport",
    "SignalType",
    "SignalStrength"
]
