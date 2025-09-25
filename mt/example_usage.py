#!/usr/bin/env python3
"""
MT5 Trading System Example Usage

This example demonstrates how to use the MT5 trading system components.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mt.logger import setup_logging, get_logger
from mt.config.settings import get_mt5_settings, validate_settings
from mt.core.connection import MT5Connection
from mt.core.trader import MT5Trader
from mt.core.llm_client import LLMClient

def main():
    """Example usage of MT5 trading system"""
    
    # Setup logging
    setup_logging(level="INFO", console_output=True, file_output=False)
    logger = get_logger(__name__)
    
    logger.info("MT5 Trading System Example")
    
    try:
        # Validate settings
        is_valid, error_msg = validate_settings()
        if not is_valid:
            logger.error(f"Settings validation failed: {error_msg}")
            return
        
        settings = get_mt5_settings()
        logger.info(f"Settings loaded - Debug mode: {settings.core.debug_mode}")
        
        # Test MT5 connection
        logger.info("Testing MT5 connection...")
        with MT5Connection() as connection:
            if not connection.is_connected:
                logger.error("Failed to connect to MT5")
                return
            
            # Get account info
            account_info = connection.get_account_info()
            if account_info:
                logger.info(f"Connected to account: {account_info.get('login')}")
                logger.info(f"Balance: {account_info.get('balance')} {account_info.get('currency')}")
            
            # Get available symbols
            symbols = connection.get_symbols()
            logger.info(f"Available symbols: {len(symbols)} (showing first 10)")
            for symbol in symbols[:10]:
                logger.info(f"  - {symbol}")
            
            # Test symbol info
            test_symbols = ["EURUSD", "GBPUSD", "XAUUSD"]
            for symbol in test_symbols:
                symbol_info = connection.symbol_info(symbol)
                if symbol_info:
                    logger.info(f"{symbol}: Bid={symbol_info.get('bid')}, Ask={symbol_info.get('ask')}")
            
            # Initialize trader
            trader = MT5Trader(connection)
            
            # Get trading summary
            summary = trader.get_trading_summary()
            logger.info(f"Trading summary: {summary}")
            
            # Get open positions
            positions = trader.get_open_positions()
            logger.info(f"Open positions: {len(positions)}")
            for pos in positions:
                logger.info(f"  Position: {pos.symbol} {pos.type} {pos.volume} lots, Profit: {pos.profit}")
            
            # Test LLM client
            logger.info("Testing LLM client...")
            llm_client = LLMClient()
            
            # Health check
            if llm_client.health_check():
                logger.info("LLM service is healthy")
                
                # Get trading signals
                signals = llm_client.get_trading_signals(["EURUSD", "GBPUSD"])
                logger.info(f"Received {len(signals)} signals from LLM")
                
                for signal in signals:
                    logger.info(f"Signal: {signal.symbol} {signal.signal_type.value} "
                              f"(confidence: {signal.confidence:.2f})")
                    
                    if signal.entry_price:
                        logger.info(f"  Entry: {signal.entry_price}, SL: {signal.stop_loss}, "
                                  f"TP: {signal.take_profit}")
                    
                    if signal.reasoning:
                        logger.info(f"  Reasoning: {signal.reasoning}")
                    
                    # Validate signal (but don't execute in example)
                    is_valid, error_msg = trader.validate_signal(signal)
                    logger.info(f"  Validation: {'✓' if is_valid else '✗'} {error_msg}")
            else:
                logger.warning("LLM service health check failed")
        
        logger.info("Example completed successfully")
        
    except Exception as e:
        logger.error(f"Example failed: {e}")

if __name__ == "__main__":
    main()
