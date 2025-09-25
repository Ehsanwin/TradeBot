from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from .openai_client import OpenAIHTTPClient, ChatMessage, create_system_prompt
from .data_types import (
    MarketData, TradingSignal, MarketReport, NewsEvent, 
    SignalType, NewsImportance, extract_currencies_from_symbol
)

logger = logging.getLogger(__name__)

class MarketReporter:
    """Generates comprehensive market analysis reports using ChatGPT"""
    
    def __init__(
        self,
        openai_client: OpenAIHTTPClient,
        model: str = "gpt-4o-mini",
        max_tokens: int = 2500,
        temperature: float = 0.4
    ):
        self.openai_client = openai_client
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
    
    def _format_technical_summary(self, market_data_list: List[MarketData]) -> str:
        """Format technical analysis summary for all symbols"""
        
        sections = ["🔍 TECHNICAL ANALYSIS SUMMARY"]
        sections.append("=" * 40)
        
        for data in market_data_list:
            if not data.technical_analysis:
                continue
                
            ta = data.technical_analysis
            sections.append(f"\n{data.symbol}:")
            
            if data.forex_quote:
                sections.append(f"  Current: {data.forex_quote.current_price}")
            
            # Key levels
            if ta.nearest_support:
                sections.append(f"  Support: {ta.nearest_support['level']:.5f} "
                              f"({ta.nearest_support['distance_percentage']:.1f}% away)")
            
            if ta.nearest_resistance:
                sections.append(f"  Resistance: {ta.nearest_resistance['level']:.5f} "
                              f"({ta.nearest_resistance['distance_percentage']:.1f}% away)")
            
            # Patterns
            if ta.patterns:
                pattern_names = [p.pattern_type for p in ta.patterns[:3]]
                sections.append(f"  Patterns: {', '.join(pattern_names)}")
        
        return "\n".join(sections)
    
    def _format_news_summary(self, all_news: List[NewsEvent]) -> str:
        """Format news summary"""
        
        if not all_news:
            return "📰 NEWS SUMMARY\n" + "=" * 40 + "\nNo significant news events found."
        
        sections = ["📰 NEWS SUMMARY"]
        sections.append("=" * 40)
        
        # Group by importance
        high_impact = [n for n in all_news if n.importance.value >= 3]
        medium_impact = [n for n in all_news if n.importance.value == 2]
        
        if high_impact:
            sections.append("\n🔴 HIGH IMPACT EVENTS:")
            for news in high_impact[:3]:
                time_str = news.timestamp.strftime("%m-%d %H:%M") if news.timestamp else "Recent"
                sections.append(f"  • [{time_str}] {news.title}")
        
        if medium_impact:
            sections.append("\n🟡 MEDIUM IMPACT EVENTS:")
            for news in medium_impact[:3]:
                time_str = news.timestamp.strftime("%m-%d %H:%M") if news.timestamp else "Recent"
                sections.append(f"  • [{time_str}] {news.title}")
        
        return "\n".join(sections)
    
    def _format_signals_summary(self, signals: List[TradingSignal]) -> str:
        """Format trading signals summary"""
        
        if not signals:
            return "📊 TRADING SIGNALS\n" + "=" * 40 + "\nNo actionable signals generated."
        
        sections = ["📊 TRADING SIGNALS"]
        sections.append("=" * 40)
        
        # Group by signal type
        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY]
        sell_signals = [s for s in signals if s.signal_type == SignalType.SELL]
        hold_signals = [s for s in signals if s.signal_type == SignalType.HOLD]
        
        if buy_signals:
            sections.append("\n📈 BUY SIGNALS:")
            for signal in buy_signals[:3]:
                conf_str = f"{signal.confidence:.0%}"
                strength = signal.strength.value.upper()
                sections.append(f"  • {signal.symbol} - {strength} ({conf_str})")
                if signal.entry_price:
                    sections.append(f"    Entry: {signal.entry_price}, SL: {signal.stop_loss}, TP: {signal.take_profit}")
        
        if sell_signals:
            sections.append("\n📉 SELL SIGNALS:")
            for signal in sell_signals[:3]:
                conf_str = f"{signal.confidence:.0%}"
                strength = signal.strength.value.upper()
                sections.append(f"  • {signal.symbol} - {strength} ({conf_str})")
                if signal.entry_price:
                    sections.append(f"    Entry: {signal.entry_price}, SL: {signal.stop_loss}, TP: {signal.take_profit}")
        
        if hold_signals:
            sections.append(f"\n⏸️  HOLD RECOMMENDATIONS: {len(hold_signals)} pairs")
        
        return "\n".join(sections)
    
    def _create_market_report_prompt(
        self,
        market_data_list: List[MarketData],
        signals: List[TradingSignal],
        all_news: List[NewsEvent]
    ) -> List[ChatMessage]:
        """Create prompt for comprehensive market report"""
        
        system_prompt = create_system_prompt(
            "market_reporter",
            "You will create a professional forex market analysis report. "
            "Synthesize technical analysis, news events, and trading signals into "
            "clear, actionable insights for traders. Focus on market themes, "
            "key levels, and risk factors."
        )
        
        # Format data sections
        technical_summary = self._format_technical_summary(market_data_list)
        news_summary = self._format_news_summary(all_news)
        signals_summary = self._format_signals_summary(signals)
        
        symbols_analyzed = [data.symbol for data in market_data_list]
        
        user_prompt = f"""
Create a comprehensive forex market analysis report based on the following data:

SYMBOLS ANALYZED: {', '.join(symbols_analyzed)}
ANALYSIS DATE: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}

{technical_summary}

{news_summary}

{signals_summary}

Please provide a market report in the following JSON format:

{{
    "title": "Market Analysis Report - [Date]",
    "summary": "2-3 sentence executive summary of market conditions",
    "market_bias": "bullish|bearish|neutral",
    "technical_summary": "Key technical levels and patterns across major pairs",
    "news_summary": "Impact of recent news events on forex markets",
    "key_themes": [
        "List of major market themes",
        "driving current price action"
    ],
    "trading_opportunities": [
        "Specific trading opportunities identified",
        "with risk considerations"
    ],
    "risk_factors": [
        "Key risks that could disrupt",
        "current market outlook"
    ],
    "market_outlook": "Short-term outlook (next 24-48 hours)",
    "recommended_actions": [
        "Specific recommendations for traders",
        "based on current analysis"
    ]
}}

REQUIREMENTS:
- Keep each section concise but informative
- Focus on actionable insights
- Highlight the most important 2-3 themes
- Consider both technical and fundamental factors
- Be objective and balanced in assessment
- Include specific price levels where relevant
"""
        
        return [
            system_prompt,
            ChatMessage(role="user", content=user_prompt)
        ]
    
    def _parse_report_response(
        self, 
        content: str, 
        market_data_list: List[MarketData],
        signals: List[TradingSignal]
    ) -> Optional[MarketReport]:
        """Parse ChatGPT response into MarketReport object"""
        
        try:
            # Extract JSON from response
            content = content.strip()
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                logger.error("No JSON found in report response")
                return None
            
            json_str = content[start_idx:end_idx]
            data = json.loads(json_str)
            
            # Extract key levels from signals
            key_levels = {}
            for signal in signals:
                levels = []
                if signal.entry_price:
                    levels.append(signal.entry_price)
                if signal.stop_loss:
                    levels.append(signal.stop_loss)
                if signal.take_profit:
                    levels.append(signal.take_profit)
                
                if levels:
                    key_levels[signal.symbol] = levels
            
            # Create report
            report = MarketReport(
                title=data.get('title', f"Market Analysis - {datetime.now().strftime('%Y-%m-%d')}"),
                summary=data.get('summary', ''),
                content=self._format_full_report_content(data),
                technical_summary=data.get('technical_summary'),
                news_summary=data.get('news_summary'),
                trading_signals=signals,
                risk_assessment=self._format_risk_assessment(data.get('risk_factors', [])),
                market_bias=data.get('market_bias', 'neutral'),
                key_levels=key_levels,
                symbols_analyzed=[data.symbol for data in market_data_list],
                timestamp=datetime.now()
            )
            
            return report
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from report response: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to parse report response: {e}")
            return None
    
    def _format_full_report_content(self, data: Dict[str, Any]) -> str:
        """Format the complete report content"""
        
        sections = []
        
        # Executive Summary
        if data.get('summary'):
            sections.append("## Executive Summary")
            sections.append(data['summary'])
        
        # Market Bias
        bias = data.get('market_bias', 'neutral').upper()
        bias_emoji = "📈" if bias == "BULLISH" else "📉" if bias == "BEARISH" else "⚖️"
        sections.append(f"\n## Market Bias: {bias_emoji} {bias}")
        
        # Key Themes
        if data.get('key_themes'):
            sections.append("\n## Key Market Themes")
            for theme in data['key_themes']:
                sections.append(f"• {theme}")
        
        # Technical Summary
        if data.get('technical_summary'):
            sections.append("\n## Technical Analysis")
            sections.append(data['technical_summary'])
        
        # News Impact
        if data.get('news_summary'):
            sections.append("\n## News Impact")
            sections.append(data['news_summary'])
        
        # Trading Opportunities
        if data.get('trading_opportunities'):
            sections.append("\n## Trading Opportunities")
            for opportunity in data['trading_opportunities']:
                sections.append(f"• {opportunity}")
        
        # Risk Factors
        if data.get('risk_factors'):
            sections.append("\n## Risk Factors")
            for risk in data['risk_factors']:
                sections.append(f"⚠️  {risk}")
        
        # Outlook
        if data.get('market_outlook'):
            sections.append("\n## Market Outlook")
            sections.append(data['market_outlook'])
        
        # Recommendations
        if data.get('recommended_actions'):
            sections.append("\n## Recommended Actions")
            for action in data['recommended_actions']:
                sections.append(f"✅ {action}")
        
        return "\n".join(sections)
    
    def _format_risk_assessment(self, risk_factors: List[str]) -> str:
        """Format risk assessment section"""
        
        if not risk_factors:
            return "Risk assessment: Standard market risks apply."
        
        return "Key Risks:\n" + "\n".join([f"• {risk}" for risk in risk_factors])
    
    def generate_market_report(
        self,
        market_data_list: List[MarketData],
        signals: List[TradingSignal]
    ) -> Optional[MarketReport]:
        """Generate comprehensive market analysis report"""
        
        if not market_data_list:
            logger.error("No market data provided for report generation")
            return None
        
        try:
            logger.info(f"Generating market report for {len(market_data_list)} symbols")
            
            # Collect all news events
            all_news = []
            for data in market_data_list:
                all_news.extend(data.related_news or [])
            
            # Remove duplicates based on title
            seen_titles = set()
            unique_news = []
            for news in all_news:
                if news.title not in seen_titles:
                    unique_news.append(news)
                    seen_titles.add(news.title)
            
            # Sort by importance and time
            unique_news.sort(key=lambda x: (x.importance.value, x.timestamp or datetime.min), reverse=True)
            
            # Create prompt
            messages = self._create_market_report_prompt(market_data_list, signals, unique_news)
            
            # Get ChatGPT response (remove problematic parameters)
            response = self.openai_client.chat_completion(
                messages=messages,
                model=self.model
            )
            
            logger.debug(f"ChatGPT report response: {response.content[:200]}...")
            
            # Parse response into report
            report = self._parse_report_response(response.content, market_data_list, signals)
            
            if report:
                logger.info(f"Generated market report: {report.title}")
                return report
            else:
                logger.warning("Failed to parse market report")
                return None
                
        except Exception as e:
            logger.error(f"Failed to generate market report: {e}")
            return None
    
    def generate_news_analysis(self, news_events: List[NewsEvent]) -> Optional[str]:
        """Generate focused news analysis"""
        
        if not news_events:
            return None
        
        try:
            system_prompt = create_system_prompt(
                "news_analyst",
                "Analyze forex market news events and their potential impact on currency pairs."
            )
            
            news_text = "\n".join([
                f"• [{news.timestamp.strftime('%m-%d %H:%M') if news.timestamp else 'Recent'}] "
                f"{news.title} (Impact: {news.importance.name})"
                for news in news_events[:10]
            ])
            
            user_prompt = f"""
Analyze these recent forex market news events and their potential impact:

{news_text}

Provide a concise analysis covering:
1. Most significant market-moving events
2. Potential currency pair impacts
3. Time-sensitive trading considerations
4. Risk factors to watch

Keep the analysis focused and actionable (max 300 words).
"""
            
            messages = [system_prompt, ChatMessage(role="user", content=user_prompt)]
            
            response = self.openai_client.chat_completion(
                messages=messages,
                model=self.model
            )
            
            return response.content
            
        except Exception as e:
            logger.error(f"Failed to generate news analysis: {e}")
            return None
