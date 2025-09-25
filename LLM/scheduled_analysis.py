#!/usr/bin/env python3
"""
Scheduled LLM Analysis for Telegram

This script runs LLM market analysis on a schedule and sends results to Telegram.
Can be run as a standalone script or integrated into your existing scheduler.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from LLM.main import LLMTradingSystem
from LLM.core.telegram_integration import TelegramNotifier
from LLM.config.settings import get_llm_settings

# Telegram integration
try:
    from telegram import Bot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

logger = logging.getLogger(__name__)

class ScheduledLLMAnalysis:
    """Handles scheduled LLM analysis and Telegram notifications"""
    
    def __init__(self):
        self.settings = get_llm_settings()
        self.llm_system: Optional[LLMTradingSystem] = None
        self.telegram_bot: Optional[Bot] = None
        self.notifier: Optional[TelegramNotifier] = None
        self.telegram_chat_ids: List[int] = []
        
        # Setup logging
        from LLM.logger import setup_logging
        setup_logging(
            level=self.settings.core.log_level,
            log_file=self.settings.core.log_file
        )
        
        logger.info("Scheduled LLM Analysis initialized")
    
    def initialize(self):
        """Initialize all components"""
        
        try:
            # Initialize LLM system
            if not self.settings.core.enabled:
                logger.warning("LLM system is disabled")
                return False
            
            self.llm_system = LLMTradingSystem()
            self.llm_system.initialize_services()
            logger.info("LLM system initialized")
            
            # Initialize Telegram if available
            bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
            chat_ids_str = os.getenv("TELEGRAM_CHAT_IDS", "")
            
            if TELEGRAM_AVAILABLE and bot_token:
                self.telegram_bot = Bot(token=bot_token)
                
                # Parse chat IDs
                if chat_ids_str:
                    try:
                        self.telegram_chat_ids = [
                            int(cid.strip()) for cid in chat_ids_str.split(",") 
                            if cid.strip().replace('-', '').isdigit()
                        ]
                        logger.info(f"Telegram configured for {len(self.telegram_chat_ids)} chats")
                    except ValueError as e:
                        logger.warning(f"Invalid chat IDs format: {e}")
                
                # Initialize notifier
                if self.telegram_chat_ids:
                    self.notifier = TelegramNotifier()
                    self.notifier.bot = self.telegram_bot
                    logger.info("Telegram notifications enabled")
                else:
                    logger.warning("No Telegram chat IDs configured")
            else:
                logger.warning("Telegram bot not configured or unavailable")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            return False
    
    async def run_analysis_and_notify(
        self, 
        symbols: Optional[List[str]] = None,
        send_detailed: bool = True
    ) -> bool:
        """Run LLM analysis and send to Telegram"""
        
        try:
            logger.info("Starting scheduled LLM analysis...")
            
            if not self.llm_system:
                logger.error("LLM system not initialized")
                return False
            
            # Run analysis with 15-minute timeframe
            results = self.llm_system.run_analysis(
                symbols=symbols,
                generate_report=True
            )
            
            if not results.get("success"):
                logger.error(f"Analysis failed: {results.get('error')}")
                return False
            
            logger.info(f"Analysis completed successfully in {results.get('analysis_time')}")
            
            # Send to Telegram if configured
            if self.notifier and self.telegram_chat_ids:
                success_count = 0
                for chat_id in self.telegram_chat_ids:
                    try:
                        success = await self.notifier.send_analysis_results(
                            chat_id=chat_id,
                            results=results,
                            send_detailed=send_detailed
                        )
                        if success:
                            success_count += 1
                            logger.info(f"Successfully sent analysis to chat {chat_id}")
                        else:
                            logger.warning(f"Failed to send analysis to chat {chat_id}")
                    except Exception as e:
                        logger.error(f"Error sending to chat {chat_id}: {e}")
                
                logger.info(f"Sent analysis to {success_count}/{len(self.telegram_chat_ids)} chats")
                return success_count > 0
            else:
                logger.info("Analysis completed (no Telegram notifications configured)")
                return True
                
        except Exception as e:
            logger.error(f"Scheduled analysis failed: {e}")
            
            # Try to send error notification
            if self.notifier and self.telegram_chat_ids:
                for chat_id in self.telegram_chat_ids:
                    try:
                        await self.notifier._send_message(
                            chat_id, 
                            f"❌ <b>Scheduled Analysis Failed</b>\n\n🚨 Error: {str(e)}"
                        )
                    except:
                        pass  # Don't fail on notification failure
            
            return False
    
    def cleanup(self):
        """Cleanup resources"""
        if self.llm_system:
            self.llm_system.cleanup()

async def run_once(
    symbols: Optional[List[str]] = None,
    detailed: bool = True
):
    """Run analysis once and exit"""
    
    scheduler = ScheduledLLMAnalysis()
    
    if not scheduler.initialize():
        logger.error("Failed to initialize scheduler")
        return False
    
    try:
        success = await scheduler.run_analysis_and_notify(
            symbols=symbols,
            send_detailed=detailed
        )
        return success
    finally:
        scheduler.cleanup()

async def run_continuous_schedule(
    interval_minutes: int = 60,
    symbols: Optional[List[str]] = None,
    detailed: bool = False  # Less detailed for scheduled runs
):
    """Run analysis continuously on schedule"""
    
    logger.info(f"Starting continuous scheduled analysis every {interval_minutes} minutes")
    
    scheduler = ScheduledLLMAnalysis()
    
    if not scheduler.initialize():
        logger.error("Failed to initialize scheduler")
        return
    
    try:
        while True:
            try:
                success = await scheduler.run_analysis_and_notify(
                    symbols=symbols,
                    send_detailed=detailed
                )
                
                if success:
                    logger.info("Scheduled analysis completed successfully")
                else:
                    logger.warning("Scheduled analysis completed with issues")
                    
            except Exception as e:
                logger.error(f"Error in scheduled run: {e}")
            
            # Wait for next run
            logger.info(f"Next analysis in {interval_minutes} minutes...")
            await asyncio.sleep(interval_minutes * 60)
            
    except KeyboardInterrupt:
        logger.info("Scheduled analysis stopped by user")
    finally:
        scheduler.cleanup()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Scheduled LLM Market Analysis")
    parser.add_argument(
        "--symbols", 
        type=str,
        help="Comma-separated symbols to analyze (e.g., EUR_USD,GBP_USD)"
    )
    parser.add_argument(
        "--once", 
        action="store_true",
        help="Run once and exit (default: continuous)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Interval in minutes for continuous mode (default: 60)"
    )
    parser.add_argument(
        "--detailed",
        action="store_true", 
        help="Send detailed signal analysis (default: summary only for scheduled)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Parse symbols
    symbols = None
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
        # Convert to OANDA format
        formatted_symbols = []
        for symbol in symbols:
            if not symbol.startswith("OANDA:"):
                if "_" in symbol:
                    formatted_symbols.append(f"OANDA:{symbol}")
                elif len(symbol) == 6:
                    formatted_symbols.append(f"OANDA:{symbol[:3]}_{symbol[3:]}")
                else:
                    formatted_symbols.append(f"OANDA:{symbol}")
            else:
                formatted_symbols.append(symbol)
        symbols = formatted_symbols
    
    try:
        if args.once:
            # Run once
            logger.info("Running one-time analysis...")
            success = asyncio.run(run_once(
                symbols=symbols,
                detailed=args.detailed or True  # Default to detailed for manual runs
            ))
            sys.exit(0 if success else 1)
        else:
            # Run continuously
            asyncio.run(run_continuous_schedule(
                interval_minutes=args.interval,
                symbols=symbols,
                detailed=args.detailed
            ))
    
    except KeyboardInterrupt:
        logger.info("Analysis stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
