#!/usr/bin/env python3
"""
Fast LLM command for Telegram integration

Optimized version that completes analysis in under 30 seconds
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

# Fast LLM imports
from LLM.fast_main import FastLLMTradingSystem
from LLM.core.telegram_integration import TelegramNotifier

logger = logging.getLogger(__name__)

class FastLLMTelegramCommand:
    """Fast LLM command handler for Telegram bot"""
    
    def __init__(self):
        self.llm_system: Optional[FastLLMTradingSystem] = None
        self.notifier = TelegramNotifier()
        self._initialized = False
    
    def _initialize_llm_system(self):
        """Initialize fast LLM system"""
        if not self._initialized:
            try:
                self.llm_system = FastLLMTradingSystem()
                self.llm_system.initialize_services()
                self._initialized = True
                logger.info("Fast LLM system initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize fast LLM system: {e}")
                raise
    
    async def llm_fast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /llmfast command for fast AI trading analysis"""
        
        chat_id = update.effective_chat.id
        
        # Check if OpenAI API key is available
        if not os.getenv("OPENAI_API_KEY"):
            await update.message.reply_text(
                "❌ <b>Fast LLM Analysis Unavailable</b>\n\n"
                "OpenAI API key not configured. Please contact admin to set up OPENAI_API_KEY.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Parse arguments
        symbols = None
        max_symbols = 3  # Default limit for speed
        
        if context.args:
            # First argument might be symbols
            symbols_arg = context.args[0] if context.args else ""
            
            if symbols_arg and not symbols_arg.isdigit():
                symbols = [s.strip().replace("/", "_") for s in symbols_arg.split(",") if s.strip()]
                
                # Convert common formats to OANDA format
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
            
            # Check if there's a max_symbols argument
            if len(context.args) > 1:
                try:
                    max_symbols = int(context.args[1])
                    max_symbols = max(1, min(max_symbols, 5))  # Limit between 1-5
                except ValueError:
                    pass
        
        # Send initial message
        progress_message = await update.message.reply_text(
            "⚡ <b>Starting FAST LLM Analysis...</b>\n\n"
            f"📊 Max Symbols: {max_symbols}\n"
            "🔍 Optimized for speed...\n\n"
            "<i>Target: Under 30 seconds</i>",
            parse_mode=ParseMode.HTML
        )
        
        try:
            # Initialize fast LLM system if needed
            self._initialize_llm_system()
            
            if not self.llm_system:
                await progress_message.edit_text(
                    "❌ <b>Fast LLM System Error</b>\n\n"
                    "Failed to initialize fast AI analysis system.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Update progress
            await progress_message.edit_text(
                "⚡ <b>Fast LLM Analysis Running</b>\n\n"
                f"📊 Analyzing: {', '.join(symbols) if symbols else f'Default top {max_symbols}'}\n"
                "🚀 Parallel processing active...\n\n"
                "<i>Please wait...</i>",
                parse_mode=ParseMode.HTML
            )
            
            # Run fast LLM analysis with 15-minute timeframe
            results = self.llm_system.run_fast_analysis(
                symbols=symbols,
                max_symbols=max_symbols
            )
            
            # Delete progress message
            await progress_message.delete()
            
            # Send fast results
            if results.get("success"):
                # Quick summary message
                analysis_time = results.get("analysis_time", "N/A")
                total_signals = results.get("total_signals", 0)
                actionable = results.get("actionable_signals", 0)
                
                # Build quick summary
                signals_text = []
                for signal in results.get("signals", []):
                    if signal["type"] in ["buy", "sell"]:
                        emoji = "📈" if signal["type"] == "buy" else "📉"
                        signals_text.append(f"{emoji} {signal['symbol']} - {signal['type'].upper()} ({signal['confidence']})")
                
                summary_text = (
                    f"⚡ <b>Fast LLM Analysis Complete</b>\n"
                    f"⏱️ Time: {analysis_time}\n"
                    f"📊 Signals: {total_signals} total, {actionable} actionable\n\n"
                )
                
                if signals_text:
                    summary_text += "<b>🎯 Actionable Signals:</b>\n"
                    summary_text += "\n".join(signals_text[:5])  # Max 5
                    summary_text += f"\n\n💡 Fast mode: Optimized analysis"
                else:
                    summary_text += "⏸️ <b>No actionable signals</b>\nMarket conditions suggest holding positions.\n\n"
                    summary_text += "💡 Consider using full analysis: /llm"
                
                await update.message.reply_text(summary_text, parse_mode=ParseMode.HTML)
                
                # Send detailed signals if any actionable ones exist
                actionable_signals = [s for s in results.get("signals", []) if s["type"] in ["buy", "sell"]]
                
                if actionable_signals:
                    await update.message.reply_text("🎯 <b>Detailed Signals:</b>", parse_mode=ParseMode.HTML)
                    
                    for signal in actionable_signals[:2]:  # Max 2 detailed signals
                        signal_type = signal["type"].upper()
                        emoji = "📈" if signal_type == "BUY" else "📉"
                        strength = signal["strength"].upper()
                        
                        detail_text = (
                            f"{emoji} <b>{signal['symbol']} - {signal_type}</b>\n"
                            f"💪 Strength: {strength} | 🎯 Confidence: {signal['confidence']}\n"
                        )
                        
                        if signal.get("entry_price"):
                            detail_text += (
                                f"💰 Entry: {signal['entry_price']}\n"
                                f"🛑 Stop: {signal['stop_loss']}\n"
                                f"🎯 Target: {signal['take_profit']}\n"
                            )
                        
                        if signal.get("reasoning"):
                            detail_text += f"\n💡 {signal['reasoning']}\n"
                        
                        if signal.get("key_factors"):
                            detail_text += f"\n📋 Key factors:\n"
                            for factor in signal["key_factors"][:2]:
                                detail_text += f"• {factor}\n"
                        
                        await update.message.reply_text(detail_text, parse_mode=ParseMode.HTML)
            else:
                error_msg = results.get("error", "Unknown error")
                await update.message.reply_text(
                    f"❌ <b>Fast Analysis Failed</b>\n\n"
                    f"🚨 Error: {error_msg}\n\n"
                    "<i>Try regular analysis: /llm</i>",
                    parse_mode=ParseMode.HTML
                )
            
        except Exception as e:
            logger.error(f"Fast LLM command error: {e}")
            
            try:
                await progress_message.delete()
            except:
                pass
            
            await update.message.reply_text(
                f"❌ <b>Fast LLM Analysis Failed</b>\n\n"
                f"🚨 Error: {str(e)}\n\n"
                "<i>Try regular analysis: /llm</i>",
                parse_mode=ParseMode.HTML
            )
    
    async def llmfast_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /llmfasthelp command"""
        
        help_text = """
        ⚡ <b>Fast LLM Trading Analysis Commands</b>
        
        <b>🎯 Fast Commands:</b>
        /llmfast - Fast AI analysis (under 30s, max 3 symbols)
        /llmfast EUR_USD,GBP_USD - Fast analysis of specific symbols
        /llmfast EURUSD 2 - Fast analysis with max 2 symbols
        /fastllm - Alternative to /llmfast
        
        <b>⚡ Speed Optimizations:</b>
        • Parallel data fetching and signal generation
        • Reduced historical data (7 days vs 30 days)
        • Optimized ChatGPT prompts (shorter responses)
        • Limited symbols (1-5 max, default 3)
        • Cached data for faster repeat requests
        
        <b>📊 What's included:</b>
        • Live forex quotes and current prices
        • Key support/resistance levels (nearest only)
        • Top chart patterns (most relevant)
        • High-impact news events only
        • Buy/sell/hold signals with confidence
        • Quick reasoning and key factors
        
        <b>🎯 Target Performance:</b>
        • Analysis time: Under 30 seconds
        • Data freshness: Real-time quotes
        • Signal quality: High confidence only
        • Resource usage: Optimized for speed
        
        <b>💡 When to use:</b>
        • Quick market check during trading hours
        • Fast signal confirmation
        • When you need immediate analysis
        • Mobile/low-bandwidth situations
        
        <b>🔄 For comprehensive analysis use:</b>
        /llm - Full detailed analysis (60-120s)
        
        <i>Fast mode trades depth for speed while maintaining accuracy</i>
        """
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
    
    def cleanup(self):
        """Cleanup fast LLM system resources"""
        if self.llm_system:
            self.llm_system.cleanup()

# Global instance for use in main Telegram bot
fast_llm_command_handler = FastLLMTelegramCommand()

async def handle_llm_fast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrapper function for fast LLM command"""
    await fast_llm_command_handler.llm_fast_command(update, context)

async def handle_llm_fast_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrapper function for fast LLM help command"""
    await fast_llm_command_handler.llmfast_help_command(update, context)
