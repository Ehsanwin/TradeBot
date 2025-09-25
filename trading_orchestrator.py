#!/usr/bin/env python3
"""
Trading Orchestrator - Main Trading Cycle
Integrates LLM Analysis + MT5 Trading + Telegram Notifications

This service runs at configurable intervals and performs:
1. Get market data 
2. Send to ChatGPT for signal generation
3. Execute trades via MT5
4. Send results to Telegram

Designed for stable, continuous operation in Docker.
"""

import asyncio
import logging
import os
import sys
import time
import signal
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

# Add project directories to path
sys.path.insert(0, str(Path(__file__).parent))

# Logging setup first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/trading_orchestrator.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Import all required modules
from LLM.fast_main import FastLLMTradingSystem
from orchestrator.bot.telegram_bot import TradingBotTelegram
from LLM.core.telegram_integration import TelegramNotifier

# Import local MT5 components for direct MT5 integration
from mt.core.connection import MT5Connection
from mt.core.trader import MT5Trader, TradeExecution, TradeResult
from LLM.core.data_types import TradingSignal

# Signal conversion is now handled directly in the trading cycle

MT5_LOCAL_AVAILABLE = True  # Use local MT5 integration

class TradingOrchestrator:
    """Main Trading Orchestrator for configurable trading cycles"""
    
    def __init__(self):
        # Initialize basic configuration first
        self.running = False
        self.trading_interval = int(os.getenv('TRADING_INTERVAL_MINUTES', '1')) * 60
        self.max_retries = 3
        self.retry_delay = 30
        
        # MT5 local connection (direct integration)
        
        # Load settings after required attributes are initialized
        self.settings = self.load_settings()
        
        # Trading components
        self.llm_system: Optional[FastLLMTradingSystem] = None
        self.mt5_connection: Optional[MT5Connection] = None
        self.mt5_trader: Optional[MT5Trader] = None
        self.telegram_notifier: Optional[TelegramNotifier] = None
        # Signal conversion is handled directly in trading cycle
        
        logger.info(f"Trading Orchestrator initialized - {self.trading_interval//60} minute cycle")
    
    def load_settings(self) -> Dict[str, Any]:
        """Load all required settings"""
        try:
            return {
                'symbols': ['EURUSD', 'GBPUSD', 'USDJPY'],  # Default symbols
                'telegram_enabled': os.getenv('TELEGRAM_ENABLED', 'false').lower() == 'true',
                'telegram_token': os.getenv('TELEGRAM_BOT_TOKEN'),
                'telegram_chat_ids': self.parse_chat_ids(os.getenv('TELEGRAM_CHAT_IDS', '')),
                'openai_api_key': os.getenv('OPENAI_API_KEY'),
                'dry_run': os.getenv('DRY_RUN', 'true').lower() == 'true',
                'mt5_local_available': True  # Use local MT5 integration
            }
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            raise
    
    def parse_chat_ids(self, chat_ids_str: str) -> List[int]:
        """Parse comma-separated chat IDs"""
        if not chat_ids_str:
            return []
        
        try:
            return [int(cid.strip()) for cid in chat_ids_str.split(',') if cid.strip()]
        except ValueError as e:
            logger.warning(f"Invalid chat IDs format: {e}")
            return []
    
    async def initialize_components(self) -> bool:
        """Initialize all trading components with stable connections"""
        retry_count = 0
        
        while retry_count < self.max_retries:
            try:
                logger.info(f"Initializing trading components (attempt {retry_count + 1}/{self.max_retries})...")
                
                # 1. Initialize LLM System with retry logic
                if not self.llm_system:
                    self.llm_system = FastLLMTradingSystem()
                    await self._initialize_llm_with_retry()
                    logger.info("✓ LLM system initialized")
                
                # 2. Signal processing configuration loaded
                logger.info("✓ Signal processing configured")
                
                # 3. Initialize MT5 Local Connection 
                if not self.settings['dry_run']:
                    await self._initialize_mt5_local_with_retry()
                    logger.info("✓ MT5 local connection and trader initialized")
                else:
                    logger.info("✓ MT5 local connection skipped (dry run mode)")
                
                # 4. Initialize Telegram Notifier (if enabled)
                if self.settings['telegram_enabled'] and self.settings['telegram_token']:
                    if not self.telegram_notifier:
                        await self._initialize_telegram_with_retry()
                        logger.info("✓ Telegram notifier initialized")
                
                logger.info("All components initialized successfully")
                return True
                
            except Exception as e:
                retry_count += 1
                logger.error(f"Component initialization failed (attempt {retry_count}): {e}")
                
                if retry_count < self.max_retries:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error("Max retries exceeded for component initialization")
                    return False
        
        return False
    
    async def run_trading_cycle(self) -> Dict[str, Any]:
        """Execute one complete trading cycle"""
        cycle_start = time.time()
        cycle_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        logger.info(f"🚀 Starting trading cycle {cycle_id}")
        
        results = {
            'cycle_id': cycle_id,
            'success': False,
            'timestamp': datetime.now().isoformat(),
            'analysis_time': 0,
            'signals_generated': 0,
            'trades_executed': 0,
            'telegram_sent': False,
            'errors': []
        }
        
        try:
            # Step 1: Generate LLM signals (fast mode)
            logger.info("📊 Step 1: Generating LLM trading signals...")
            llm_results = self.llm_system.run_fast_analysis(
                symbols=self.settings['symbols'],
                max_symbols=3
            )
            
            if not llm_results.get('success'):
                error_msg = f"LLM analysis failed: {llm_results.get('error')}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
                return results
            
            results['analysis_time'] = float(llm_results.get('analysis_time', '0').rstrip('s'))
            results['signals_generated'] = len(llm_results.get('signals', []))
            
            logger.info(f"✅ Generated {results['signals_generated']} signals in {results['analysis_time']:.2f}s")
            
            # Step 2: Execute trades via local MT5
            if llm_results.get('signals') and not self.settings['dry_run']:
                logger.info("💱 Step 2: Processing and executing trades via local MT5...")
                
                # Import signal types once
                from LLM.core.data_types import SignalType, SignalStrength
                
                # Convert LLM signal dicts to TradingSignal objects
                trading_signals = []
                for signal_dict in llm_results['signals']:
                    # Convert dict to TradingSignal object
                    try:
                        trading_signal = TradingSignal(
                            symbol=signal_dict.get('symbol', ''),
                            signal_type=SignalType(signal_dict.get('type', 'hold').lower()),
                            strength=SignalStrength(signal_dict.get('strength', 'moderate').lower()),
                            confidence=float(signal_dict.get('confidence', 0.0)),
                            entry_price=float(signal_dict['entry_price']) if signal_dict.get('entry_price') is not None else None,
                            stop_loss=float(signal_dict['stop_loss']) if signal_dict.get('stop_loss') is not None else None,
                            take_profit=float(signal_dict['take_profit']) if signal_dict.get('take_profit') is not None else None,
                            reasoning=signal_dict.get('reasoning'),
                            key_factors=signal_dict.get('key_factors', []),
                            risks=signal_dict.get('risks', []),
                            timeframe=signal_dict.get('timeframe'),
                            timestamp=datetime.now(),
                            expires_at=None
                        )
                        trading_signals.append(trading_signal)
                    except Exception as e:
                        logger.warning(f"Failed to convert signal {signal_dict.get('symbol', 'UNKNOWN')}: {e}")
                        continue
                
                # Filter actionable signals (minimum confidence check)
                min_confidence = float(os.getenv('MIN_CONFIDENCE', '0.70'))
                actionable_signals = [s for s in trading_signals if s.confidence >= min_confidence]
                
                logger.info(f"Converted {len(trading_signals)} signals, {len(actionable_signals)} actionable")
                
                executed_count = 0
                for trading_signal in actionable_signals:
                    try:
                        # Execute the trade via local MT5
                        execution_result = await self._execute_trade_with_retry(trading_signal)
                        
                        if execution_result and execution_result.get('success'):
                            executed_count += 1
                            logger.info(f"✅ Executed {trading_signal.signal_type.value} {trading_signal.symbol} "
                                      f"@ {trading_signal.entry_price or 'Market'} (Ticket: {execution_result.get('ticket', 'N/A')})")
                        else:
                            error_msg = f"Failed to execute {trading_signal.symbol}: {execution_result.get('error', 'Unknown error')}"
                            logger.warning(error_msg)
                            results['errors'].append(error_msg)
                            
                    except Exception as e:
                        error_msg = f"Trade execution error for {trading_signal.symbol}: {e}"
                        logger.error(error_msg)
                        results['errors'].append(error_msg)
                
                results['trades_executed'] = executed_count
                logger.info(f"✅ Executed {executed_count}/{len(actionable_signals)} trades")
            
            elif self.settings['dry_run']:
                logger.info("🔄 DRY RUN MODE - Processing signals for validation only")
                # Filter actionable signals based on confidence
                min_confidence = float(os.getenv('MIN_CONFIDENCE', '0.70'))
                actionable_signals = [s for s in llm_results['signals'] if float(s.get('confidence', 0)) >= min_confidence]
                results['trades_executed'] = len(actionable_signals)  # Simulate execution count
                logger.info(f"✅ Would execute {len(actionable_signals)} trades (DRY RUN)")
            
            else:
                logger.info("ℹ️ No signals to execute or trading disabled")
            
            # Step 3: Send to Telegram
            if self.telegram_notifier and self.settings['telegram_chat_ids']:
                logger.info("📱 Step 3: Sending results to Telegram...")
                
                try:
                    message = self.format_telegram_message(llm_results, results)
                    
                    success_count = 0
                    for chat_id in self.settings['telegram_chat_ids']:
                        try:
                            await self.telegram_notifier._send_message(chat_id, message)
                            success_count += 1
                        except Exception as e:
                            logger.error(f"Failed to send to chat {chat_id}: {e}")
                    
                    results['telegram_sent'] = success_count > 0
                    logger.info(f"✅ Sent to {success_count}/{len(self.settings['telegram_chat_ids'])} Telegram chats")
                    
                except Exception as e:
                    error_msg = f"Telegram notification failed: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            # Cycle complete
            cycle_time = time.time() - cycle_start
            results['success'] = True
            results['cycle_time'] = round(cycle_time, 2)
            
            logger.info(f"🎯 Cycle {cycle_id} completed in {cycle_time:.2f}s - "
                       f"Signals: {results['signals_generated']}, "
                       f"Trades: {results['trades_executed']}, "
                       f"Telegram: {'✓' if results['telegram_sent'] else '✗'}")
            
        except Exception as e:
            error_msg = f"Trading cycle error: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
        
        return results
    
    def format_telegram_message(self, llm_results: Dict, cycle_results: Dict) -> str:
        """Format trading cycle results for Telegram"""
        
        signals = llm_results.get('signals', [])
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"🤖 <b>Trading Cycle Report</b>\n"
        message += f"⏰ {timestamp} UTC\n"
        message += f"🔄 Cycle: {cycle_results['cycle_id']}\n\n"
        
        # Analysis summary
        message += f"📊 <b>Analysis:</b>\n"
        message += f"• Time: {cycle_results['analysis_time']:.1f}s\n"
        message += f"• Signals: {cycle_results['signals_generated']}\n\n"
        
        # Trading summary
        message += f"💱 <b>Trading:</b>\n"
        if self.settings['dry_run']:
            message += f"• Mode: DRY RUN\n"
        else:
            message += f"• Executed: {cycle_results['trades_executed']} trades\n"
            message += f"• Via: Local MT5\n"
        
        # Signal details (if any)
        if signals:
            message += f"\n📈 <b>Signals Generated:</b>\n"
            for i, signal in enumerate(signals[:3], 1):  # Limit to 3 signals
                signal_type = signal.get('type', 'UNKNOWN')
                emoji = "🟢" if signal_type == "BUY" else "🔴" if signal_type == "SELL" else "⚪"
                
                message += f"{emoji} <b>{signal.get('symbol')}</b> - {signal_type}\n"
                message += f"   Confidence: {signal.get('confidence', 'N/A')}\n"
                if signal.get('reasoning'):
                    reasoning = signal['reasoning'][:100] + "..." if len(signal['reasoning']) > 100 else signal['reasoning']
                    message += f"   💡 {reasoning}\n"
                message += "\n"
        
        # Errors (if any)
        if cycle_results['errors']:
            message += f"⚠️ <b>Issues:</b>\n"
            for error in cycle_results['errors'][:2]:  # Limit errors shown
                message += f"• {error[:100]}...\n" if len(error) > 100 else f"• {error}\n"
        
        message += f"\n🔄 Next cycle in {self.trading_interval//60} minute{'s' if self.trading_interval//60 != 1 else ''}"
        
        return message
    
    async def _initialize_llm_with_retry(self):
        """Initialize LLM system with retry logic"""
        for attempt in range(self.max_retries):
            try:
                self.llm_system.initialize_services()
                return True
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"LLM init attempt {attempt + 1} failed: {e}, retrying...")
                    await asyncio.sleep(self.retry_delay)
                else:
                    raise
        return False
    
    async def _initialize_mt5_local_with_retry(self):
        """Initialize MT5 local connection with retry logic"""
        for attempt in range(self.max_retries):
            try:
                # Initialize MT5 connection
                self.mt5_connection = MT5Connection()
                
                # Test connection
                if not self.mt5_connection.connect():
                    error_msg = self.mt5_connection.status.last_error or "Unknown connection error"
                    raise Exception(f"MT5 local connection failed: {error_msg}")
                
                # Initialize local trader
                self.mt5_trader = MT5Trader(self.mt5_connection)
                
                account_info = self.mt5_connection.get_account_info()
                account_number = account_info.get('login', 'Unknown') if account_info else 'Unknown'
                logger.info(f"✅ MT5 local connected - Account: {account_number}")
                return True
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"MT5 local init attempt {attempt + 1} failed: {e}, retrying...")
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(f"MT5 local initialization failed after {self.max_retries} attempts: {e}")
                    raise
        return False
    
    async def _initialize_telegram_with_retry(self):
        """Initialize Telegram notifier with retry logic"""
        for attempt in range(self.max_retries):
            try:
                self.telegram_notifier = TelegramNotifier()
                # Test send to validate
                return True
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Telegram init attempt {attempt + 1} failed: {e}, retrying...")
                    await asyncio.sleep(self.retry_delay)
                else:
                    raise
        return False
    
    async def _execute_trade_with_retry(self, trading_signal) -> Dict[str, Any]:
        """Execute trade via local MT5 with retry logic"""
        if not self.mt5_trader:
            return {
                'success': False,
                'error': 'MT5 local trader not available - running in analysis-only mode'
            }
        
        for attempt in range(self.max_retries):
            try:
                # Check MT5 local connection before trade
                if not self.mt5_connection.ensure_connection():
                    logger.warning("MT5 local connection lost, reconnecting...")
                    if not self.mt5_connection.reconnect():
                        raise Exception("MT5 local reconnection failed")
                
                # Execute the trade via local trader (synchronous call)
                execution_result = self.mt5_trader.execute_signal(trading_signal)
                
                # Convert TradeExecution to dict format expected by orchestrator
                return {
                    'success': execution_result.result == TradeResult.SUCCESS,
                    'ticket': execution_result.ticket,
                    'volume': execution_result.volume,
                    'price': execution_result.price,
                    'error': execution_result.error_message if execution_result.result != TradeResult.SUCCESS else None
                }
                    
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Trade execution attempt {attempt + 1} failed: {e}, retrying...")
                    await asyncio.sleep(5)  # Shorter retry delay for trades
                else:
                    return {
                        'success': False,
                        'error': str(e)
                    }
        
        return {'success': False, 'error': 'Max retries exceeded'}
    
    async def run_continuous(self):
        """Run continuous trading cycles"""
        logger.info(f"🎯 Starting continuous {self.trading_interval//60}-minute trading cycles")
        
        self.running = True
        cycle_count = 0
        last_health_check = time.time()
        
        while self.running:
            try:
                cycle_count += 1
                
                # Run trading cycle
                results = await self.run_trading_cycle()
                
                # Health check every hour
                if time.time() - last_health_check > 3600:  # 1 hour
                    await self.health_check()
                    last_health_check = time.time()
                
                # Wait for next cycle
                if self.running:
                    logger.info(f"⏳ Waiting {self.trading_interval//60} minutes for next cycle...")
                    await asyncio.sleep(self.trading_interval)
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                break
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                # Wait before retry
                await asyncio.sleep(30)
    
    async def health_check(self):
        """Perform system health check"""
        try:
            logger.info("🔍 Performing health check...")
            
            # Check MT5 local connection
            if self.mt5_connection:
                if self.mt5_connection.check_connection():
                    account_info = self.mt5_connection.get_account_info()
                    balance = account_info.get('balance', 'N/A') if account_info else 'N/A'
                    logger.info(f"✅ MT5 local healthy - Balance: {balance}")
                else:
                    logger.warning(f"⚠️ MT5 local health issue: {self.mt5_connection.status.last_error or 'Unknown'}")
                    
                    # Try to reconnect
                    if self.mt5_connection.reconnect():
                        logger.info("✅ MT5 local reconnected successfully")
                    else:
                        logger.error(f"❌ MT5 local reconnection failed: {self.mt5_connection.status.last_error or 'Unknown'}")
            else:
                logger.info("ℹ️ MT5 local connection not initialized")
            
            logger.info("✅ Health check completed")
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
    
    def shutdown(self):
        """Graceful shutdown"""
        logger.info("🛑 Shutting down Trading Orchestrator...")
        
        self.running = False
        
        try:
            if self.mt5_connection:
                # Close local MT5 connection
                try:
                    self.mt5_connection.disconnect()
                    logger.info("✅ MT5 local connection closed")
                except Exception as close_error:
                    logger.warning(f"Could not properly close MT5 connection: {close_error}")
            
            if self.llm_system:
                self.llm_system.cleanup()
                
        except Exception as e:
            logger.error(f"Shutdown error: {e}")
        
        logger.info("✅ Trading Orchestrator shutdown complete")

# Signal handlers
orchestrator_instance = None

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    global orchestrator_instance
    if orchestrator_instance:
        orchestrator_instance.shutdown()
    sys.exit(0)

async def main():
    """Main entry point"""
    global orchestrator_instance
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Create orchestrator
        orchestrator_instance = TradingOrchestrator()
        
        # Initialize components
        if not await orchestrator_instance.initialize_components():
            logger.error("❌ Failed to initialize components")
            sys.exit(1)
        
        logger.info("✅ Trading Orchestrator ready - starting continuous operation")
        
        # Run continuous trading
        await orchestrator_instance.run_continuous()
        
    except KeyboardInterrupt:
        logger.info("Trading orchestrator interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        if orchestrator_instance:
            orchestrator_instance.shutdown()

if __name__ == "__main__":
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    # Run orchestrator
    asyncio.run(main())
