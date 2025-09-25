#!/usr/bin/env python3
"""
AI Trading Analysis Telegram Bot

This bot provides AI-powered trading analysis through Telegram commands.
It focuses on LLM-based market analysis and trading insights using advanced
AI models for comprehensive and fast trading analysis.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Any, Dict, List, Optional

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler
)

# Import project configuration
from orchestrator.config.settings import get_settings
from orchestrator.core.logging_setup import configure_logging

# Setup logging with configuration first
settings = get_settings()
configure_logging(
    level=settings.core.logging.level,
    file_path=settings.core.logging.file,
    max_size=settings.core.logging.max_size,
    backup_count=settings.core.logging.backup_count
)
logger = logging.getLogger(__name__)

# Import LLM integration
try:
    from LLM.telegram_command import handle_llm_command, handle_llm_help_command, llm_command_handler
    from LLM.telegram_command_fast import handle_llm_fast_command, handle_llm_fast_help_command, fast_llm_command_handler
    LLM_AVAILABLE = True
    logger.info("LLM integration loaded successfully (including fast mode)")
except ImportError as e:
    LLM_AVAILABLE = False
    logger.warning(f"LLM integration not available: {e}")


class TradingBotTelegram:
    """AI-powered Telegram bot for trading analysis using LLM models."""
    
    def __init__(self):
        self.settings = settings  # Use the global settings object
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.allowed_chat_ids = set(self.settings.telegram_allowed_chat_ids)
        
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
            
        logger.info("Initializing AI Trading Bot")
        logger.info(f"Allowed chat IDs: {self.allowed_chat_ids}")

    def _is_authorized(self, chat_id: int) -> bool:
        """Check if the chat_id is authorized to use the bot."""
        if not self.allowed_chat_ids:
            return True  # If no restrictions set, allow all
        return chat_id in self.allowed_chat_ids



    async def _send_long_message(self, update: Update, text: str, parse_mode=ParseMode.HTML):
        """Send long messages by splitting them if necessary."""
        max_length = 4096
        
        if len(text) <= max_length:
            await update.message.reply_text(text, parse_mode=parse_mode)
            return
            
        # Split long messages
        lines = text.split('\n')
        current_message = ""
        
        for line in lines:
            if len(current_message + line + '\n') > max_length:
                if current_message:
                    await update.message.reply_text(current_message, parse_mode=parse_mode)
                    current_message = line + '\n'
                else:
                    # Single line is too long, need to split it
                    await update.message.reply_text(line[:max_length], parse_mode=parse_mode)
            else:
                current_message += line + '\n'
        
        if current_message:
            await update.message.reply_text(current_message, parse_mode=parse_mode)

    # Command Handlers
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("❌ Unauthorized access.")
            return

        welcome_text = """
            🤖 <b>AI Trading Analysis Bot</b>

            Welcome! I'm your AI-powered trading assistant. I provide intelligent market analysis using advanced AI models.

            <b>🚀 Quick Start:</b>
            • /llmfast EUR/USD - Fast AI analysis (30s)
            • /llm EURUSD,GBPUSD - Full AI analysis (60-120s)
            • /help - See all commands

            <i>Ready for AI-powered trading insights! 🧠📈</i>
            """
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command with simplified command list."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("❌ Unauthorized access.")
            return

        help_text = """
            🤖 <b>AI Trading Bot Commands</b>

            <b>📊 Basic Commands:</b>
            /start - Welcome message
            /help - Show this help message

            <b>🤖 AI Trading Analysis:</b>
            /llm [symbols] - Full AI market analysis with ChatGPT (60-120s)
            /llmfast [symbols] - Fast AI analysis (under 30s, limited data)
            /llmhelp - Detailed help for AI analysis commands

            <b>Alternative Commands:</b>
            /ai [symbols] - Same as /llm (alternative command)
            /fastllm [symbols] - Same as /llmfast (alternative command)

            <b>Examples:</b>
            /llm EURUSD,GBPUSD       (AI analysis of EUR/USD and GBP/USD)
            /llmfast EUR/USD         (Quick AI analysis of EUR/USD)
            /ai USDJPY              (AI analysis using alternative command)

            <b>💡 Features:</b>
            • <b>/llm</b> - Comprehensive analysis with technical indicators, news, and detailed insights
            • <b>/llmfast</b> - Quick analysis with essential information only
            • Supports multiple currency pairs in one command
            • AI-powered insights and trading recommendations

            <i>💡 Tip: Use /llmfast for quick insights, /llm for detailed analysis!</i>
            """
        await self._send_long_message(update, help_text)




    async def llm_analysis_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /llm command for AI trading analysis"""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("❌ Unauthorized access.")
            return

        if not LLM_AVAILABLE:
            await update.message.reply_text(
                "❌ <b>LLM Analysis Unavailable</b>\n\n"
                "AI trading analysis is not available. Please contact admin.",
                parse_mode=ParseMode.HTML
            )
            return
        
        await handle_llm_command(update, context)

    async def llm_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /llmhelp command"""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("❌ Unauthorized access.")
            return

        if not LLM_AVAILABLE:
            await update.message.reply_text(
                "❌ <b>LLM Analysis Unavailable</b>\n\n"
                "AI trading analysis is not available. Please contact admin.",
                parse_mode=ParseMode.HTML
            )
            return
        
        await handle_llm_help_command(update, context)

    async def llm_fast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /llmfast command for fast AI trading analysis"""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("❌ Unauthorized access.")
            return

        if not LLM_AVAILABLE:
            await update.message.reply_text(
                "❌ <b>Fast LLM Analysis Unavailable</b>\n\n"
                "AI trading analysis is not available. Please contact admin.",
                parse_mode=ParseMode.HTML
            )
            return
        
        await handle_llm_fast_command(update, context)

    async def llm_fast_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /llmfasthelp command"""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("❌ Unauthorized access.")
            return

        if not LLM_AVAILABLE:
            await update.message.reply_text(
                "❌ <b>Fast LLM Analysis Unavailable</b>\n\n"
                "AI trading analysis is not available. Please contact admin.",
                parse_mode=ParseMode.HTML
            )
            return
        
        await handle_llm_fast_help_command(update, context)

    async def unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle unknown commands."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("❌ Unauthorized access.")
            return

        text = """
            ❓ <b>Unknown Command</b>

            I don't recognize that command. Here are the available commands:

            • /help - Show all commands  
            • /llmfast [symbols] - Fast AI analysis (30s)
            • /llm [symbols] - Full AI analysis (60-120s)
            • /ai [symbols] - Same as /llm
            • /llmhelp - Help for LLM commands

            Type /help for more details.
            """
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors."""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.message:
            await update.message.reply_text(
                "🚨 An error occurred. Please try again later."
            )

    def setup_handlers(self, application: Application):
        """Setup command handlers for simplified LLM-focused bot."""
        # Basic commands
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        
        # LLM/AI commands
        application.add_handler(CommandHandler("llm", self.llm_analysis_command))
        application.add_handler(CommandHandler("ai", self.llm_analysis_command))  # Alternative command
        application.add_handler(CommandHandler("llmhelp", self.llm_help_command))
        
        # Fast LLM commands
        application.add_handler(CommandHandler("llmfast", self.llm_fast_command))
        application.add_handler(CommandHandler("fastllm", self.llm_fast_command))  # Alternative
        application.add_handler(CommandHandler("llmfasthelp", self.llm_fast_help_command))
        
        # Unknown command handler
        application.add_handler(MessageHandler(filters.COMMAND, self.unknown_command))
        
        # Error handler
        application.add_error_handler(self.error_handler)

    async def run(self):
        """Run the bot."""
        if not self.settings.telegram_enabled:
            logger.warning("Telegram bot is disabled in configuration")
            return
            
        logger.info("Starting Telegram bot...")
        
        # Create application
        application = Application.builder().token(self.bot_token).build()
        
        # Setup handlers
        self.setup_handlers(application)
        
        try:
            # Initialize and start the application manually
            async with application:
                logger.info("Bot is running. Press Ctrl+C to stop.")
                await application.start()
                await application.updater.start_polling(
                    allowed_updates=Update.ALL_TYPES,
                    drop_pending_updates=True
                )
                
                # Keep running until interrupted
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    logger.info("Received interrupt signal")
                finally:
                    await application.updater.stop()
                    
                    # Cleanup LLM resources
                    if LLM_AVAILABLE:
                        try:
                            llm_command_handler.cleanup()
                            fast_llm_command_handler.cleanup()
                        except Exception as e:
                            logger.warning(f"Failed to cleanup LLM resources: {e}")
                    
        except Exception as e:
            logger.error(f"Bot error: {e}")
            raise


async def main():
    """Main entry point."""
    try:
        bot = TradingBotTelegram()
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
