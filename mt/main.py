#!/usr/bin/env python3
"""
MT5 Trading System Main Entry Point

This system integrates with MetaTrader5 to execute trades based on LLM-generated signals.
It connects to the LLM analysis service, processes trading signals, and executes trades
through MT5 with comprehensive risk management.

Usage:
    python main.py [--symbols EURUSD,GBPUSD] [--dry-run] [--once] [--debug]
"""

import argparse
import asyncio
import sys
import time
import signal
from pathlib import Path
from typing import List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mt.logger import setup_logging, get_logger
from mt.config.settings import get_mt5_settings, validate_settings
from mt.core.connection import MT5Connection
from mt.core.trader import MT5Trader
from mt.core.llm_client import LLMClient

logger = get_logger(__name__)

class MT5TradingSystem:
    """Main MT5 Trading System"""
    
    def __init__(self):
        self.settings = get_mt5_settings()
        self.setup_logging()
        
        # Initialize components
        self.connection: Optional[MT5Connection] = None
        self.trader: Optional[MT5Trader] = None
        self.llm_client: Optional[LLMClient] = None
        self.running = False
        
        logger.info("MT5 Trading System initialized")
    
    def setup_logging(self):
        """Setup logging configuration"""
        config = self.settings.core.logging
        setup_logging(
            level=config.level,
            log_file=config.file,
            format_string=config.format,
            max_size=config.max_size,
            backup_count=config.backup_count,
            console_output=config.console_output,
            file_output=config.file_output
        )
    
    def initialize_components(self) -> bool:
        """
        Initialize all system components
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing MT5 Trading System components...")
            
            # Validate settings
            is_valid, error_msg = validate_settings()
            if not is_valid:
                logger.error(f"Settings validation failed: {error_msg}")
                return False
            
            # Initialize MT5 connection
            self.connection = MT5Connection()
            if not self.connection.connect():
                logger.error("Failed to connect to MT5 terminal")
                return False
            
            # Initialize trader
            self.trader = MT5Trader(self.connection)
            
            # Initialize LLM client
            self.llm_client = LLMClient()
            
            # Test LLM service health
            if not self.llm_client.health_check():
                logger.warning("LLM service health check failed - signals may not be available")
            
            logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            return False
    
    def run_trading_cycle(self, symbols: Optional[List[str]] = None) -> dict:
        """
        Run a single trading cycle
        
        Args:
            symbols: List of symbols to trade (uses default if None)
        
        Returns:
            dict: Cycle results
        """
        cycle_start = time.time()
        results = {
            "success": False,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "signals_received": 0,
            "trades_executed": 0,
            "errors": []
        }
        
        try:
            if not symbols:
                symbols = self.settings.core.trading.default_symbols
            
            logger.info(f"Starting trading cycle for symbols: {symbols}")
            
            # Check if we should request new analysis
            if not self.llm_client.should_request_analysis():
                logger.debug("Skipping analysis - too soon since last request")
                results["success"] = True
                results["message"] = "Skipped - analysis interval not reached"
                return results
            
            # Get trading signals from LLM
            signals = self.llm_client.get_trading_signals(symbols)
            results["signals_received"] = len(signals)
            
            if not signals:
                logger.info("No trading signals received from LLM")
                results["success"] = True
                results["message"] = "No signals received"
                return results
            
            # Process each signal
            executed_trades = 0
            for signal in signals:
                try:
                    logger.info(f"Processing signal: {signal.symbol} {signal.signal_type.value}")
                    
                    # Execute the trade
                    execution_result = self.trader.execute_signal(signal)
                    
                    if execution_result.result.value == "success":
                        executed_trades += 1
                        logger.info(f"Trade executed successfully - Ticket: {execution_result.ticket}")
                    else:
                        error_msg = f"Trade execution failed: {execution_result.error_message}"
                        logger.warning(error_msg)
                        results["errors"].append(error_msg)
                
                except Exception as e:
                    error_msg = f"Error processing signal for {signal.symbol}: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            results["trades_executed"] = executed_trades
            results["success"] = True
            
            cycle_time = time.time() - cycle_start
            logger.info(f"Trading cycle completed in {cycle_time:.2f}s - {executed_trades}/{len(signals)} trades executed")
            
        except Exception as e:
            error_msg = f"Trading cycle error: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
        
        return results
    
    def run_continuous(self, symbols: Optional[List[str]] = None):
        """
        Run continuous trading loop
        
        Args:
            symbols: List of symbols to trade
        """
        logger.info("Starting continuous trading mode")
        self.running = True
        
        cycle_count = 0
        last_health_check = time.time()
        health_check_interval = self.settings.core.health_check_interval
        
        while self.running:
            try:
                cycle_count += 1
                logger.debug(f"Starting trading cycle #{cycle_count}")
                
                # Run trading cycle
                results = self.run_trading_cycle(symbols)
                
                # Log cycle summary
                if results["success"]:
                    logger.info(f"Cycle #{cycle_count}: {results.get('message', 'Completed')} - "
                              f"Signals: {results['signals_received']}, Trades: {results['trades_executed']}")
                else:
                    logger.error(f"Cycle #{cycle_count} failed with {len(results['errors'])} errors")
                
                # Health check
                current_time = time.time()
                if current_time - last_health_check > health_check_interval:
                    self.perform_health_check()
                    last_health_check = current_time
                
                # Wait before next cycle
                analysis_interval = self.settings.core.llm.analysis_interval_minutes * 60
                time.sleep(analysis_interval)
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down...")
                break
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                time.sleep(30)  # Wait 30 seconds before retry
    
    def perform_health_check(self):
        """Perform system health check"""
        try:
            logger.debug("Performing system health check")
            
            # Check MT5 connection
            if not self.connection.check_connection():
                logger.warning("MT5 connection check failed, attempting reconnection...")
                if not self.connection.reconnect():
                    logger.error("MT5 reconnection failed")
            
            # Check LLM service
            if not self.llm_client.health_check():
                logger.warning("LLM service health check failed")
            
            # Get trading summary
            summary = self.trader.get_trading_summary()
            logger.info(f"Trading Summary - Balance: {summary.get('account_balance', 0)}, "
                       f"Open Positions: {summary.get('open_positions', 0)}, "
                       f"Win Rate (30d): {summary.get('win_rate_30d', 0)}%")
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
    
    def shutdown(self):
        """Shutdown the trading system"""
        logger.info("Shutting down MT5 Trading System...")
        
        self.running = False
        
        if self.connection:
            self.connection.disconnect()
        
        logger.info("MT5 Trading System shutdown complete")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    global trading_system
    if trading_system:
        trading_system.shutdown()
    sys.exit(0)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="MT5 Trading System")
    parser.add_argument(
        "--symbols",
        type=str,
        help="Comma-separated list of symbols to trade (e.g., EURUSD,GBPUSD)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Enable dry run mode (no actual trades)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (don't run continuously)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    global trading_system
    trading_system = None
    
    try:
        # Create system instance
        trading_system = MT5TradingSystem()
        
        # Override settings based on arguments
        if args.dry_run:
            trading_system.settings.core.dry_run = True
            logger.info("DRY RUN MODE ENABLED - No actual trades will be executed")
        
        if args.debug:
            trading_system.settings.core.debug_mode = True
            trading_system.settings.core.logging.level = "DEBUG"
            trading_system.setup_logging()  # Reconfigure logging
        
        # Check if system is enabled
        if not trading_system.settings.core.enabled:
            logger.error("MT5 Trading System is disabled in configuration")
            sys.exit(1)
        
        # Initialize components
        if not trading_system.initialize_components():
            logger.error("Component initialization failed")
            sys.exit(1)
        
        # Parse symbols
        symbols = None
        if args.symbols:
            symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
            logger.info(f"Using symbols from command line: {symbols}")
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Run system
        if args.once:
            logger.info("Running single trading cycle...")
            results = trading_system.run_trading_cycle(symbols)
            
            if results["success"]:
                print(f"✅ Trading cycle completed successfully")
                print(f"   Signals received: {results['signals_received']}")
                print(f"   Trades executed: {results['trades_executed']}")
                if results.get("errors"):
                    print(f"   Errors: {len(results['errors'])}")
                sys.exit(0)
            else:
                print(f"❌ Trading cycle failed")
                for error in results.get("errors", []):
                    print(f"   Error: {error}")
                sys.exit(1)
        else:
            logger.info("Starting continuous trading mode...")
            trading_system.run_continuous(symbols)
        
    except KeyboardInterrupt:
        logger.info("Trading system interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"System error: {e}")
        sys.exit(1)
    finally:
        if trading_system:
            trading_system.shutdown()

if __name__ == "__main__":
    main()
