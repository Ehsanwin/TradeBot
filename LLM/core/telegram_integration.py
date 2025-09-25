from __future__ import annotations

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from .data_types import TradingSignal, MarketReport, SignalType, SignalStrength

logger = logging.getLogger(__name__)

class TelegramFormatter:
    """Formats LLM trading analysis for Telegram messages"""
    
    @staticmethod
    def format_signal(signal: TradingSignal) -> str:
        """Format a single trading signal for Telegram"""
        
        # Signal type emoji
        type_emoji = {
            SignalType.BUY: "📈",
            SignalType.SELL: "📉", 
            SignalType.HOLD: "⏸️",
            SignalType.CLOSE_LONG: "🔻",
            SignalType.CLOSE_SHORT: "🔺"
        }.get(signal.signal_type, "❓")
        
        # Strength emoji
        strength_emoji = {
            SignalStrength.WEAK: "🟡",
            SignalStrength.MODERATE: "🟠",
            SignalStrength.STRONG: "🔴", 
            SignalStrength.VERY_STRONG: "🟣"
        }.get(signal.strength, "⚪")
        
        lines = [
            f"{type_emoji} <b>{signal.symbol} - {signal.signal_type.value.upper()}</b>",
            f"{strength_emoji} Strength: {signal.strength.value.upper()}",
            f"🎯 Confidence: {signal.confidence:.0%}"
        ]
        
        # Add price levels if available
        if signal.entry_price:
            lines.append(f"💰 Entry: {signal.entry_price:.5f}")
        if signal.stop_loss:
            lines.append(f"🛑 Stop Loss: {signal.stop_loss:.5f}")
        if signal.take_profit:
            lines.append(f"🎯 Take Profit: {signal.take_profit:.5f}")
        
        # Add reasoning if available
        if signal.reasoning:
            lines.append(f"💡 <i>{signal.reasoning}</i>")
        
        # Add key factors
        if signal.key_factors:
            lines.append("\n<b>Key Factors:</b>")
            for factor in signal.key_factors[:3]:  # Limit to 3 factors
                lines.append(f"• {factor}")
        
        # Add risks
        if signal.risks:
            lines.append("\n<b>⚠️ Risks:</b>")
            for risk in signal.risks[:2]:  # Limit to 2 risks
                lines.append(f"• {risk}")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_signals_summary(signals: List[TradingSignal]) -> str:
        """Format multiple signals into a summary"""
        
        if not signals:
            return "📊 <b>LLM Trading Analysis</b>\n\n⏸️ No actionable signals generated.\nMarket conditions suggest holding positions."
        
        # Group signals by type
        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY]
        sell_signals = [s for s in signals if s.signal_type == SignalType.SELL] 
        hold_signals = [s for s in signals if s.signal_type == SignalType.HOLD]
        
        lines = [
            "🤖 <b>LLM Trading Analysis Results</b>",
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
            ""
        ]
        
        # Summary stats
        total_signals = len(signals)
        actionable = len(buy_signals) + len(sell_signals)
        
        lines.extend([
            f"📊 Total Signals: {total_signals}",
            f"🎯 Actionable: {actionable}",
            f"⏸️ Hold: {len(hold_signals)}",
            ""
        ])
        
        # Buy signals
        if buy_signals:
            lines.append("📈 <b>BUY SIGNALS:</b>")
            for signal in buy_signals[:3]:  # Limit to top 3
                lines.append(f"• {signal.symbol} ({signal.confidence:.0%}) - {signal.strength.value}")
            lines.append("")
        
        # Sell signals  
        if sell_signals:
            lines.append("📉 <b>SELL SIGNALS:</b>")
            for signal in sell_signals[:3]:  # Limit to top 3
                lines.append(f"• {signal.symbol} ({signal.confidence:.0%}) - {signal.strength.value}")
            lines.append("")
        
        # Hold recommendations
        if hold_signals and len(hold_signals) <= 5:
            lines.append("⏸️ <b>HOLD RECOMMENDATIONS:</b>")
            for signal in hold_signals:
                lines.append(f"• {signal.symbol} ({signal.confidence:.0%})")
        elif hold_signals:
            lines.append(f"⏸️ <b>HOLD RECOMMENDATIONS:</b> {len(hold_signals)} pairs")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_market_report(report: MarketReport) -> str:
        """Format market report for Telegram"""
        
        lines = [
            f"📋 <b>{report.title}</b>",
            f"⏰ {report.timestamp.strftime('%Y-%m-%d %H:%M UTC')}",
            ""
        ]
        
        # Market bias
        bias_emoji = {
            "bullish": "📈",
            "bearish": "📉", 
            "neutral": "⚖️"
        }.get(report.market_bias, "⚖️")
        
        lines.extend([
            f"{bias_emoji} <b>Market Bias: {(report.market_bias or 'NEUTRAL').upper()}</b>",
            "",
            f"📝 <b>Executive Summary:</b>",
            f"{report.summary}",
            ""
        ])
        
        # Technical summary
        if report.technical_summary:
            lines.extend([
                "🔍 <b>Technical Analysis:</b>",
                f"{report.technical_summary}",
                ""
            ])
        
        # News summary
        if report.news_summary:
            lines.extend([
                "📰 <b>News Impact:</b>",
                f"{report.news_summary}",
                ""
            ])
        
        # Risk assessment
        if report.risk_assessment:
            lines.extend([
                "⚠️ <b>Risk Assessment:</b>",
                f"{report.risk_assessment}",
                ""
            ])
        
        # Trading signals count
        if report.trading_signals:
            actionable = len([s for s in report.trading_signals if s.signal_type in [SignalType.BUY, SignalType.SELL]])
            lines.extend([
                "📊 <b>Trading Signals:</b>",
                f"Total: {len(report.trading_signals)} | Actionable: {actionable}",
                ""
            ])
        
        lines.append("<i>Generated by ChatGPT Market Analysis</i>")
        
        return "\n".join(lines)
    
    @staticmethod
    def split_long_message(text: str, max_length: int = 4096) -> List[str]:
        """Split long messages into multiple parts for Telegram"""
        
        if len(text) <= max_length:
            return [text]
        
        messages = []
        lines = text.split('\n')
        current_message = ""
        
        for line in lines:
            # Check if adding this line would exceed the limit
            if len(current_message + line + '\n') > max_length:
                if current_message:
                    messages.append(current_message.rstrip())
                    current_message = line + '\n'
                else:
                    # Single line is too long, need to split it
                    while len(line) > max_length:
                        messages.append(line[:max_length])
                        line = line[max_length:]
                    current_message = line + '\n'
            else:
                current_message += line + '\n'
        
        if current_message:
            messages.append(current_message.rstrip())
        
        return messages
    
    @staticmethod
    def format_error_message(error: str) -> str:
        """Format error message for Telegram"""
        return f"❌ <b>LLM Analysis Error</b>\n\n🚨 {error}\n\n<i>Please try again later or check the configuration.</i>"

class TelegramNotifier:
    """Handles sending LLM analysis to Telegram"""
    
    def __init__(self, telegram_bot_instance=None):
        self.bot = telegram_bot_instance
        self.formatter = TelegramFormatter()
    
    async def send_analysis_results(
        self, 
        chat_id: int, 
        results: Dict[str, Any],
        send_detailed: bool = True
    ) -> bool:
        """Send LLM analysis results to Telegram chat"""
        
        try:
            if not results.get("success"):
                error_msg = self.formatter.format_error_message(results.get("error", "Unknown error"))
                await self._send_message(chat_id, error_msg)
                return False
            
            # Send summary first
            signals_data = results.get("signals", [])
            signals = []
            
            # Convert dict signals back to TradingSignal objects for formatting
            for signal_data in signals_data:
                try:
                    signal = TradingSignal(
                        symbol=signal_data["symbol"],
                        signal_type=SignalType(signal_data["type"]),
                        strength=SignalStrength(signal_data["strength"]), 
                        confidence=float(signal_data["confidence"]),
                        entry_price=signal_data.get("entry_price"),
                        stop_loss=signal_data.get("stop_loss"),
                        take_profit=signal_data.get("take_profit"),
                        reasoning=signal_data.get("reasoning"),
                        key_factors=signal_data.get("key_factors", []),
                        risks=signal_data.get("risks", [])
                    )
                    signals.append(signal)
                except Exception as e:
                    logger.warning(f"Failed to convert signal data: {e}")
                    continue
            
            # Send signals summary
            summary_text = self.formatter.format_signals_summary(signals)
            await self._send_message(chat_id, summary_text)
            
            # Send market report if available
            report_data = results.get("report")
            if report_data and report_data.get("content"):
                try:
                    # Create a simplified report object for formatting
                    from ..core.data_types import MarketReport
                    report = MarketReport(
                        title=report_data.get("title", "Market Analysis"),
                        summary=report_data.get("summary", ""),
                        content=report_data.get("content", ""),
                        market_bias=report_data.get("market_bias"),
                        technical_summary=report_data.get("technical_summary"),
                        news_summary=report_data.get("news_summary"),
                        trading_signals=signals
                    )
                    
                    report_text = self.formatter.format_market_report(report)
                    await self._send_message(chat_id, report_text)
                    
                except Exception as e:
                    logger.error(f"Failed to send market report: {e}")
            
            # Send detailed signals if requested and there are actionable ones
            if send_detailed:
                actionable_signals = [s for s in signals if s.signal_type in [SignalType.BUY, SignalType.SELL]]
                
                if actionable_signals:
                    detail_header = "🎯 <b>Detailed Signal Analysis</b>\n"
                    await self._send_message(chat_id, detail_header)
                    
                    for signal in actionable_signals[:3]:  # Limit to top 3 detailed
                        signal_text = self.formatter.format_signal(signal)
                        await self._send_message(chat_id, signal_text)
            
            # Send analysis stats
            stats_text = self._format_analysis_stats(results)
            await self._send_message(chat_id, stats_text)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send analysis results to Telegram: {e}")
            try:
                error_msg = self.formatter.format_error_message(f"Failed to send results: {str(e)}")
                await self._send_message(chat_id, error_msg)
            except:
                pass  # Don't fail on error message failure
            return False
    
    def _format_analysis_stats(self, results: Dict[str, Any]) -> str:
        """Format analysis statistics"""
        
        analysis_time = results.get("analysis_time", "N/A")
        symbols_count = len(results.get("symbols_analyzed", []))
        
        return (
            f"📈 <b>Analysis Complete</b>\n"
            f"⏱️ Processing Time: {analysis_time}\n"
            f"📊 Symbols Analyzed: {symbols_count}\n"
            f"🤖 Powered by ChatGPT"
        )
    
    async def _send_message(self, chat_id: int, text: str):
        """Send a single message, handling long text splitting"""
        
        if not self.bot:
            logger.warning("No Telegram bot instance available")
            return
        
        messages = self.formatter.split_long_message(text)
        
        for message in messages:
            try:
                # Use the bot's context to send message
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Failed to send message to Telegram: {e}")
                # Try sending without HTML formatting as fallback
                try:
                    # Remove HTML tags for fallback
                    clean_text = message.replace('<b>', '').replace('</b>', '')
                    clean_text = clean_text.replace('<i>', '').replace('</i>', '')
                    
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=clean_text
                    )
                except Exception as e2:
                    logger.error(f"Failed to send fallback message: {e2}")
                    raise
