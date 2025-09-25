#!/usr/bin/env python3
"""
Example usage of the LLM Trading Analysis System

This script demonstrates how to use the LLM trading system programmatically.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Try to load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Note: python-dotenv not installed, relying on system environment variables")

from LLM import LLMTradingSystem, get_llm_settings
from LLM.core.data_types import SignalType

def basic_example():
    """Basic usage example"""
    print("🤖 LLM Trading Analysis - Basic Example")
    print("=" * 50)
    
    # Check if API key is available
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("Please add your OpenAI API key to your .env file:")
        print("OPENAI_API_KEY=your_api_key_here")
        return
    
    system = None
    try:
        # Initialize system
        system = LLMTradingSystem()
        system.initialize_services()
        
        # Run analysis with default symbols
        print("📊 Running analysis with default symbols...")
        results = system.run_analysis()
        
        # Print results
        system.print_results(results)
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if system:
            system.cleanup()

def custom_symbols_example():
    """Example with custom symbols"""
    print("\n🎯 Custom Symbols Example")
    print("=" * 50)
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        return
    
    system = None
    try:
        # Initialize system
        system = LLMTradingSystem()
        system.initialize_services()
        
        # Custom symbols to analyze
        custom_symbols = ["OANDA:EUR_USD", "OANDA:GBP_USD", "OANDA:XAU_USD"]
        
        print(f"📊 Analyzing custom symbols: {', '.join(custom_symbols)}")
        results = system.run_analysis(symbols=custom_symbols, generate_report=True)
        
        if results['success']:
            print("\n✅ Analysis completed successfully!")
            
            # Show actionable signals only
            actionable = [s for s in results['signals'] if s['type'] in ['buy', 'sell']]
            if actionable:
                print(f"\n🎯 Found {len(actionable)} actionable signals:")
                for signal in actionable:
                    print(f"  • {signal['symbol']}: {signal['type'].upper()} "
                          f"(confidence: {signal['confidence']})")
            else:
                print("\n⏸️  No actionable signals - market conditions suggest holding")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if system:
            system.cleanup()

def configuration_example():
    """Example showing configuration options"""
    print("\n⚙️ Configuration Example")
    print("=" * 50)
    
    # Show current configuration
    settings = get_llm_settings()
    
    print("Current Configuration:")
    print(f"  • OpenAI Model: {settings.core.openai.model}")
    print(f"  • Max Tokens: {settings.core.openai.max_tokens}")
    print(f"  • Temperature: {settings.core.openai.temperature}")
    print(f"  • Backend URL: {settings.backend_base_url}")
    print(f"  • Default Symbols: {len(settings.core.analysis.default_symbols)} symbols")
    print(f"  • Analysis Days: {settings.core.analysis.analysis_days}")
    print(f"  • News Lookback: {settings.core.analysis.news_lookback_hours} hours")
    print(f"  • Debug Mode: {settings.core.debug_mode}")
    
    print("\nTo customize configuration, set environment variables:")
    print("  OPENAI_MODEL=gpt-4  # Use GPT-4 instead of gpt-4o-mini")
    print("  OPENAI_TEMPERATURE=0.3  # More conservative analysis")
    print("  LLM_ANALYSIS_DAYS=60  # Look back 60 days instead of 30")
    print("  LLM_DEBUG=true  # Enable debug logging")

def main():
    """Main example runner"""
    print("🚀 LLM Trading Analysis System - Examples")
    print("=" * 60)
    
    # Check system requirements
    print("Checking system requirements...")
    
    # Check if TradeBot API is accessible (basic check)
    settings = get_llm_settings()
    import requests
    try:
        response = requests.get(f"{settings.backend_base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ TradeBot API accessible")
        else:
            print("⚠️  TradeBot API responding but may have issues")
    except requests.exceptions.RequestException:
        print("❌ TradeBot API not accessible - make sure TradeBot is running")
        print(f"   Expected URL: {settings.backend_base_url}/health")
    
    # Run examples
    try:
        basic_example()
        custom_symbols_example() 
        configuration_example()
        
        print("\n🎉 Examples completed!")
        print("\nNext steps:")
        print("  1. Customize your .env file with preferred settings")
        print("  2. Run: python LLM/main.py --symbols YOUR_SYMBOLS")
        print("  3. Check logs in logs/llm_trading.log for detailed information")
        
    except KeyboardInterrupt:
        print("\n👋 Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
