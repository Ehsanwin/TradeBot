#!/usr/bin/env python3
"""
Orchestrator Main Entry Point

This is the main entry point for the trading bot orchestrator.
It can run the Telegram bot based on configuration.
"""

import asyncio
import logging
import os
import sys

# Import settings first to configure logging
from orchestrator.config.settings import get_settings

# Setup logging with configuration
from orchestrator.core.logging_setup import configure_logging

# Get settings to configure logging
settings = get_settings()
configure_logging(
    level=settings.core.logging.level,
    file_path=settings.core.logging.file,
    max_size=settings.core.logging.max_size,
    backup_count=settings.core.logging.backup_count
)
from orchestrator.bot.telegram_bot import TradingBotTelegram

logger = logging.getLogger(__name__)


async def main():
    """Main orchestrator entry point."""
    # Settings already loaded above for logging configuration
    
    logger.info("Starting Trading Bot Orchestrator")
    logger.info(f"Backend URL: {settings.backend_base_url}")
    logger.info(f"Telegram enabled: {settings.telegram_enabled}")
    
    if not settings.telegram_enabled:
        logger.warning("Telegram bot is disabled. Enable it by setting TELEGRAM_ENABLED=true")
        return
    
    # Check required environment variables
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is required")
        sys.exit(1)
    
    try:
        # Initialize and run Telegram bot
        logger.info("Initializing Telegram bot...")
        bot = TradingBotTelegram()
        await bot.run()
        
    except KeyboardInterrupt:
        logger.info("Orchestrator stopped by user")
    except Exception as e:
        logger.error(f"Orchestrator crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
