#!/usr/bin/env python3
"""
Fast LLM Trading Analysis System

Optimized version for sub-30 second analysis with parallel processing
and reduced data fetching.

Usage:
    python LLM/fast_main.py [--symbols EUR_USD,GBP_USD]
"""

import argparse
import sys
import time
from pathlib import Path
from typing import List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from LLM.logger import setup_logging, get_logger
from LLM.config.settings import get_llm_settings
from LLM.core.openai_client import OpenAIHTTPClient
from LLM.core.optimized_data_service import OptimizedMarketDataService
from LLM.core.fast_signal_generator import FastSignalGenerator
from LLM.core.data_types import SignalType

logger = get_logger(__name__)

class FastLLMTradingSystem:
    """Fast LLM Trading Analysis System optimized for speed"""
    
    def __init__(self):
        self.settings = get_llm_settings()
        self.setup_logging()
        
        # Initialize components
        self.openai_client: Optional[OpenAIHTTPClient] = None
        self.market_data_service: Optional[OptimizedMarketDataService] = None
        self.signal_generator: Optional[FastSignalGenerator] = None
        
        logger.info("Fast LLM Trading System initialized")
    
    def setup_logging(self):
        """Setup logging configuration"""
        setup_logging(
            level=self.settings.core.log_level,
            log_file=self.settings.core.log_file,
            format_string="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    def initialize_services(self):
        """Initialize all services with fast parameters"""
        try:
            # Validate OpenAI API key
            if not self.settings.openai_api_key:
                raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
            
            # Initialize OpenAI client
            self.openai_client = OpenAIHTTPClient(
                api_key=self.settings.openai_api_key,
                api_base=self.settings.core.openai.api_base,
                timeout=20,  # Reduced timeout
                retries=2,   # Reduced retries
                backoff=0.5  # Faster backoff
            )
            
            # Initialize optimized market data service
            self.market_data_service = OptimizedMarketDataService(
                base_url=self.settings.backend_base_url,
                timeout=15,  # Reduced timeout
                retries=1,   # Reduced retries 
                max_workers=3  # Parallel requests
            )
            
            # Set shorter cache TTL for fresh data
            self.market_data_service.set_cache_ttl(60)  # 1 minute cache
            
            # Initialize fast signal generator
            self.signal_generator = FastSignalGenerator(
                openai_client=self.openai_client,
                model=self.settings.core.openai.model,
                max_tokens=1000,  # Reduced tokens
                temperature=0.2,  # Lower temperature for speed
                confidence_threshold=self.settings.core.analysis.signal_confidence_threshold,
                max_workers=3  # Parallel signal generation
            )
            
            logger.info("All fast services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize fast services: {e}")
            raise
    
    def run_fast_analysis(
        self, 
        symbols: Optional[List[str]] = None,
        max_symbols: int = 3  # Limit symbols for speed
    ) -> dict:
        """Run fast market analysis optimized for speed"""
        
        if not symbols:
            symbols = self.settings.core.analysis.default_symbols
        
        # Limit symbols for speed
        if len(symbols) > max_symbols:
            symbols = symbols[:max_symbols]
            logger.info(f"Limited to {max_symbols} symbols for speed: {symbols}")
        
        logger.info(f"Starting FAST analysis for symbols: {symbols}")
        start_time = time.time()
        
        try:
            # 1. Fetch market data in parallel (optimized)
            logger.info("Step 1: Fetching market data (parallel)...")
            market_data_list = self.market_data_service.get_market_data_parallel(
                symbols=symbols,
                timeframe="15",   # 15-minute timeframe
                analysis_days=7,  # Reduced from 30 to 7 days
                news_hours=12,    # Reduced from 24 to 12 hours
                max_workers=3     # Parallel fetching
            )
            
            if not market_data_list:
                logger.error("No market data retrieved")
                return {"success": False, "error": "No market data retrieved"}
            
            logger.info(f"Retrieved market data for {len(market_data_list)} symbols")
            
            # 2. Generate trading signals in parallel
            logger.info("Step 2: Generating trading signals (parallel)...")
            signals = self.signal_generator.generate_signals_parallel(market_data_list)
            
            actionable_signals = self.signal_generator.filter_actionable_signals(signals)
            
            logger.info(f"Generated {len(signals)} total signals, {len(actionable_signals)} actionable")
            
            # 3. Quick summary (no detailed report for speed)
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
                "report": None  # Skip report for speed
            }
            
            logger.info(f"FAST analysis completed successfully in {elapsed:.2f}s")
            return results
            
        except Exception as e:
            logger.error(f"Fast analysis failed: {e}")
            return {"success": False, "error": str(e)}
    
    def print_fast_results(self, results: dict):
        """Print fast analysis results"""
        
        if not results.get("success"):
            print(f"❌ Fast analysis failed: {results.get('error')}")
            return
        
        print("\n" + "="*60)
        print("⚡ FAST LLM TRADING ANALYSIS RESULTS")
        print("="*60)
        
        print(f"⏱️  Analysis Time: {results['analysis_time']} (FAST MODE)")
        print(f"📊 Symbols: {', '.join(results['symbols_analyzed'])}")
        print(f"📈 Signals Generated: {results['total_signals']} ({results['actionable_signals']} actionable)")
        
        # Print signals
        if results.get("signals"):
            print("\n📊 TRADING SIGNALS (FAST):")
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
        
        print(f"\n⚡ Fast mode: Optimized for speed with parallel processing")
        print("="*60)
    
    def cleanup(self):
        """Cleanup resources"""
        if self.openai_client:
            self.openai_client.close()
        if self.market_data_service:
            self.market_data_service.close()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Fast LLM Trading Analysis System")
    parser.add_argument(
        "--symbols", 
        type=str,
        help="Comma-separated list of symbols to analyze (e.g., EUR_USD,GBP_USD)"
    )
    parser.add_argument(
        "--max-symbols",
        type=int,
        default=3,
        help="Maximum number of symbols to analyze for speed (default: 3)"
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
        system = FastLLMTradingSystem()
        
        # Override debug mode if specified
        if args.debug:
            system.settings.core.debug_mode = True
            system.settings.core.log_level = "DEBUG"
            system.setup_logging()
        
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
        
        # Run fast analysis
        results = system.run_fast_analysis(symbols=symbols, max_symbols=args.max_symbols)
        
        # Print results
        system.print_fast_results(results)
        
        # Exit with appropriate code
        sys.exit(0 if results.get("success") else 1)
        
    except KeyboardInterrupt:
        logger.info("Fast analysis interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fast system error: {e}")
        sys.exit(1)
    finally:
        if system:
            system.cleanup()

if __name__ == "__main__":
    main()
