#!/usr/bin/env python3
"""
LLM Trading Analysis System

This system uses ChatGPT to analyze forex market data and generate trading signals.
It fetches data from TradeBot APIs, normalizes the data, and uses AI analysis to:

1. Generate trading signals (buy/sell/hold)
2. Analyze market news impact  
3. Create comprehensive market reports
4. Provide actionable trading insights

Usage:
    python main.py [--symbols EUR_USD,GBP_USD] [--report-only] [--config path/to/config]
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path
from typing import List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from LLM.logger import setup_logging, get_logger
from LLM.config.settings import get_llm_settings
from LLM.core.openai_client import OpenAIHTTPClient
from LLM.core.market_data_service import MarketDataService
from LLM.core.signal_generator import SignalGenerator
from LLM.core.market_reporter import MarketReporter
from LLM.core.data_types import SignalType

logger = get_logger(__name__)

class LLMTradingSystem:
    """Main LLM Trading Analysis System"""
    
    def __init__(self):
        self.settings = get_llm_settings()
        self.setup_logging()
        
        # Initialize components
        self.openai_client: Optional[OpenAIHTTPClient] = None
        self.market_data_service: Optional[MarketDataService] = None
        self.signal_generator: Optional[SignalGenerator] = None
        self.market_reporter: Optional[MarketReporter] = None
        
        logger.info("LLM Trading System initialized")
    
    def setup_logging(self):
        """Setup logging configuration"""
        setup_logging(
            level=self.settings.core.log_level,
            log_file=self.settings.core.log_file,
            format_string="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    def initialize_services(self):
        """Initialize all services"""
        try:
            # Validate OpenAI API key
            if not self.settings.openai_api_key:
                raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
            
            # Initialize OpenAI client
            self.openai_client = OpenAIHTTPClient(
                api_key=self.settings.openai_api_key,
                api_base=self.settings.core.openai.api_base,
                timeout=self.settings.core.openai.timeout,
                retries=self.settings.core.openai.retries,
                backoff=self.settings.core.openai.backoff
            )
            
            # Initialize market data service
            self.market_data_service = MarketDataService(
                base_url=self.settings.backend_base_url,
                timeout=self.settings.core.data_sources.timeout,
                retries=self.settings.core.data_sources.retries
            )
            
            # Set cache TTL
            cache_duration = self.settings.core.cache_duration_minutes * 60
            self.market_data_service.set_cache_ttl(cache_duration)
            
            # Initialize signal generator
            self.signal_generator = SignalGenerator(
                openai_client=self.openai_client,
                model=self.settings.core.openai.model,
                max_tokens=self.settings.core.openai.max_tokens,
                temperature=self.settings.core.openai.temperature,
                confidence_threshold=self.settings.core.analysis.signal_confidence_threshold
            )
            
            # Initialize market reporter
            self.market_reporter = MarketReporter(
                openai_client=self.openai_client,
                model=self.settings.core.openai.model,
                max_tokens=self.settings.core.openai.max_tokens + 500,  # More tokens for reports
                temperature=self.settings.core.openai.temperature
            )
            
            logger.info("All services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise
    
    def run_analysis(
        self, 
        symbols: Optional[List[str]] = None,
        generate_report: bool = True
    ) -> dict:
        """Run complete market analysis"""
        
        if not symbols:
            symbols = self.settings.core.analysis.default_symbols
        
        logger.info(f"Starting market analysis for symbols: {symbols}")
        start_time = time.time()
        
        try:
            # 1. Fetch market data
            logger.info("Step 1: Fetching market data...")
            market_data_list = self.market_data_service.get_market_data(
                symbols=symbols,
                timeframe="15",  # 15-minute timeframe
                analysis_days=self.settings.core.analysis.analysis_days,
                news_hours=self.settings.core.analysis.news_lookback_hours
            )
            
            if not market_data_list:
                logger.error("No market data retrieved")
                return {"success": False, "error": "No market data retrieved"}
            
            logger.info(f"Retrieved market data for {len(market_data_list)} symbols")
            
            # 2. Generate trading signals
            logger.info("Step 2: Generating trading signals...")
            signals = self.signal_generator.generate_signals(market_data_list)
            
            actionable_signals = self.signal_generator.filter_actionable_signals(signals)
            
            logger.info(f"Generated {len(signals)} total signals, {len(actionable_signals)} actionable")
            
            # 3. Generate market report (if requested)
            report = None
            if generate_report:
                logger.info("Step 3: Generating market report...")
                report = self.market_reporter.generate_market_report(market_data_list, signals)
                
                if report:
                    logger.info(f"Generated market report: {report.title}")
                else:
                    logger.warning("Failed to generate market report")
            
            # 4. Compile results
            elapsed = time.time() - start_time
            
            results = {
                "success": True,
                "analysis_time": f"{elapsed:.2f}s",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "symbols_analyzed": symbols,
                "market_data_count": len(market_data_list),
                "total_signals": len(signals),
                "actionable_signals": len(actionable_signals),
                "signals": [
                    {
                        "symbol": s.symbol,
                        "type": s.signal_type.value,
                        "strength": s.strength.value,
                        "confidence": f"{s.confidence:.2f}",
                        "reasoning": s.reasoning,
                        "entry_price": s.entry_price,
                        "stop_loss": s.stop_loss,
                        "take_profit": s.take_profit,
                        "key_factors": s.key_factors,
                        "risks": s.risks
                    }
                    for s in signals
                ],
                "report": {
                    "title": report.title if report else None,
                    "summary": report.summary if report else None,
                    "market_bias": report.market_bias if report else None,
                    "content": report.content if report else None
                } if report else None
            }
            
            logger.info(f"Analysis completed successfully in {elapsed:.2f}s")
            return results
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return {"success": False, "error": str(e)}
    
    def print_results(self, results: dict):
        """Print analysis results in a formatted way"""
        
        if not results.get("success"):
            print(f"❌ Analysis failed: {results.get('error')}")
            return
        
        print("\n" + "="*60)
        print("🤖 LLM TRADING ANALYSIS RESULTS")
        print("="*60)
        
        print(f"⏱️  Analysis Time: {results['analysis_time']}")
        print(f"📊 Symbols: {', '.join(results['symbols_analyzed'])}")
        print(f"📈 Signals Generated: {results['total_signals']} ({results['actionable_signals']} actionable)")
        
        # Print signals
        if results.get("signals"):
            print("\n📊 TRADING SIGNALS:")
            print("-" * 40)
            
            for signal in results["signals"]:
                signal_type = signal["type"].upper()
                emoji = "📈" if signal_type == "BUY" else "📉" if signal_type == "SELL" else "⏸️"
                
                print(f"\n{emoji} {signal['symbol']} - {signal_type}")
                print(f"   Strength: {signal['strength'].upper()} | Confidence: {signal['confidence']}")
                
                if signal.get("entry_price"):
                    print(f"   Entry: {signal['entry_price']} | SL: {signal['stop_loss']} | TP: {signal['take_profit']}")
                
                if signal.get("reasoning"):
                    print(f"   💡 {signal['reasoning']}")
        
        # Print report summary
        if results.get("report") and results["report"]["summary"]:
            print("\n📋 MARKET REPORT:")
            print("-" * 40)
            print(f"Title: {results['report']['title']}")
            print(f"Bias: {results['report']['market_bias'].upper()}")
            print(f"\n{results['report']['summary']}")
        
        print("\n" + "="*60)
    
    def cleanup(self):
        """Cleanup resources"""
        if self.openai_client:
            self.openai_client.close()
        if self.market_data_service:
            self.market_data_service.close()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="LLM Trading Analysis System")
    parser.add_argument(
        "--symbols", 
        type=str,
        help="Comma-separated list of symbols to analyze (e.g., EUR_USD,GBP_USD)"
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Only generate market report without individual signals"
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip market report generation"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    system = None
    try:
        # Create system instance
        system = LLMTradingSystem()
        
        # Override debug mode if specified
        if args.debug:
            system.settings.core.debug_mode = True
            system.settings.core.log_level = "DEBUG"
            system.setup_logging()  # Reconfigure logging
        
        # Check if system is enabled
        if not system.settings.core.enabled:
            logger.error("LLM Trading System is disabled in configuration")
            sys.exit(1)
        
        # Initialize services
        system.initialize_services()
        
        # Parse symbols
        symbols = None
        if args.symbols:
            symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
        
        # Run analysis
        generate_report = not args.no_report
        results = system.run_analysis(symbols=symbols, generate_report=generate_report)
        
        # Print results
        system.print_results(results)
        
        # Exit with appropriate code
        sys.exit(0 if results.get("success") else 1)
        
    except KeyboardInterrupt:
        logger.info("Analysis interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"System error: {e}")
        sys.exit(1)
    finally:
        if system:
            system.cleanup()

if __name__ == "__main__":
    main()
