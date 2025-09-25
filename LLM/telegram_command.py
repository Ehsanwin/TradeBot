#!/usr/bin/env python3
"""
Standalone LLM command for Telegram integration

This can be imported and added to your existing Telegram bot
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

# LLM imports
from LLM.main import LLMTradingSystem
from LLM.core.telegram_integration import TelegramNotifier

logger = logging.getLogger(__name__)

class LLMTelegramCommand:
    """LLM command handler for Telegram bot"""
    
    def __init__(self):
        self.llm_system: Optional[LLMTradingSystem] = None
        self.notifier = TelegramNotifier()
        self._initialized = False
    
    def _initialize_llm_system(self):
        """Initialize LLM system if not already done"""
        if not self._initialized:
            try:
                self.llm_system = LLMTradingSystem()
                self.llm_system.initialize_services()
                self._initialized = True
                logger.info("LLM system initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize LLM system: {e}")
                raise
    
    async def llm_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /llm command for AI trading analysis"""
        
        chat_id = update.effective_chat.id
        
        # Check if OpenAI API key is available
        if not os.getenv("OPENAI_API_KEY"):
            await update.message.reply_text(
                "❌ <b>LLM Analysis Unavailable</b>\n\n"
                "OpenAI API key not configured. Please contact admin to set up OPENAI_API_KEY.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Parse arguments
        symbols = None
        if context.args:
            # Parse symbols from command arguments
            symbols_arg = " ".join(context.args)
            symbols = [s.strip().replace("/", "_") for s in symbols_arg.split(",") if s.strip()]
            
            # Convert common formats to OANDA format
            formatted_symbols = []
            for symbol in symbols:
                if not symbol.startswith("OANDA:"):
                    # Convert formats like EUR_USD or EURUSD to OANDA:EUR_USD
                    if "_" in symbol:
                        formatted_symbols.append(f"OANDA:{symbol}")
                    elif len(symbol) == 6:
                        formatted_symbols.append(f"OANDA:{symbol[:3]}_{symbol[3:]}")
                    else:
                        formatted_symbols.append(f"OANDA:{symbol}")
                else:
                    formatted_symbols.append(symbol)
            symbols = formatted_symbols
        
        # Send initial message
        progress_message = await update.message.reply_text(
            "🤖 <b>Starting LLM Trading Analysis...</b>\n\n"
            "📊 Fetching market data...\n"
            "🔍 Analyzing with ChatGPT...\n"
            "📝 Generating report...\n\n"
            "<i>This may take 30-60 seconds...</i>",
            parse_mode=ParseMode.HTML
        )
        
        try:
            # Initialize LLM system if needed
            self._initialize_llm_system()
            
            if not self.llm_system:
                await progress_message.edit_text(
                    "❌ <b>LLM System Error</b>\n\n"
                    "Failed to initialize AI analysis system.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Update progress
            await progress_message.edit_text(
                "🤖 <b>LLM Trading Analysis</b>\n\n"
                f"📊 Analyzing symbols: {', '.join(symbols) if symbols else 'Default symbols'}\n"
                "🔍 ChatGPT processing market data...\n\n"
                "<i>Please wait...</i>",
                parse_mode=ParseMode.HTML
            )
            
            # Run LLM analysis with 15-minute timeframe
            results = self.llm_system.run_analysis(
                symbols=symbols,
                generate_report=True
            )
            
            # Delete progress message
            await progress_message.delete()
            
            # Set up notifier with bot reference
            self.notifier.bot = context.bot
            
            # Send results to Telegram
            success = await self.notifier.send_analysis_results(
                chat_id=chat_id,
                results=results,
                send_detailed=True
            )
            
            if not success:
                await update.message.reply_text(
                    "⚠️ <b>Analysis Completed with Issues</b>\n\n"
                    "Some parts of the analysis may not have been sent successfully. "
                    "Check logs for details.",
                    parse_mode=ParseMode.HTML
                )
            
        except Exception as e:
            logger.error(f"LLM command error: {e}")
            
            try:
                await progress_message.delete()
            except:
                pass
            
            await update.message.reply_text(
                f"❌ <b>LLM Analysis Failed</b>\n\n"
                f"🚨 Error: {str(e)}\n\n"
                "<i>Please try again later or check the system configuration.</i>",
                parse_mode=ParseMode.HTML
            )
    
    async def llm_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /llmhelp command"""
        
        help_text = """
        🤖 <b>LLM Trading Analysis Commands</b>
        
        <b>🎯 Main Command:</b>
        /llm - Run AI trading analysis with default symbols
        /llm EUR_USD,GBP_USD - Analyze specific symbols
        /llm EUR/USD,GBP/USD - Alternative format
        
        <b>📊 What it does:</b>
        • Fetches live forex quotes, technical analysis, and news
        • Uses ChatGPT to analyze market conditions
        • Generates buy/sell/hold signals with confidence levels
        • Provides detailed reasoning and risk assessment
        • Creates comprehensive market reports
        
        <b>📝 Output includes:</b>
        • Trading signals (Buy/Sell/Hold) with confidence %
        • Entry, stop loss, and take profit levels
        • Market bias (Bullish/Bearish/Neutral)
        • Technical analysis summary
        • News impact assessment
        • Risk factors and key levels
        
        <b>⚙️ Requirements:</b>
        • OpenAI API key must be configured
        • TradeBot API must be running
        • Analysis takes 30-60 seconds to complete
        
        <b>💡 Examples:</b>
        /llm - Analyze default pairs
        /llm EURUSD - Analyze EUR/USD only
        /llm EUR_USD,GBP_USD,XAU_USD - Multiple pairs
        
        <i>Powered by ChatGPT for intelligent market analysis</i>
        """
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
    
    def cleanup(self):
        """Cleanup LLM system resources"""
        if self.llm_system:
            self.llm_system.cleanup()

# Global instance for use in main Telegram bot
llm_command_handler = LLMTelegramCommand()

async def handle_llm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrapper function for LLM command"""
    await llm_command_handler.llm_command(update, context)

async def handle_llm_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrapper function for LLM help command"""
    await llm_command_handler.llm_help_command(update, context)
