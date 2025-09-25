#!/usr/bin/env python3
"""
MT5 System Quick Test Script

This script performs quick tests of the MT5 trading system to verify everything is working.

Usage:
    python mt/test_mt5.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test if all imports work correctly"""
    print("🧪 Testing imports...")
    
    try:
        from mt.logger import setup_logging, get_logger
        print("   ✅ Logger module")
        
        from mt.config.settings import get_mt5_settings, validate_settings
        print("   ✅ Settings module")
        
        from mt.core.connection import MT5Connection
        print("   ✅ Connection module")
        
        from mt.core.trader import MT5Trader, TradingSignal, SignalType, SignalStrength
        print("   ✅ Trader module")
        
        from mt.core.llm_client import LLMClient
        print("   ✅ LLM Client module")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_configuration():
    """Test configuration loading"""
    print("⚙️  Testing configuration...")
    
    try:
        from mt.config.settings import get_mt5_settings, validate_settings
        
        # Load settings
        settings = get_mt5_settings()
        print("   ✅ Settings loaded")
        
        # Validate settings
        is_valid, error_msg = validate_settings()
        if is_valid:
            print("   ✅ Settings validation passed")
        else:
            print(f"   ⚠️  Settings validation: {error_msg}")
        
        # Print some key settings
        print(f"   📊 Dry run mode: {settings.core.dry_run}")
        print(f"   📊 Default symbols: {settings.core.trading.default_symbols}")
        print(f"   📊 Default volume: {settings.core.trading.default_volume}")
        print(f"   📊 Max risk: {settings.core.trading.max_risk_percent}%")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Configuration test failed: {e}")
        return False

def test_mt5_availability():
    """Test MT5 module availability"""
    print("🔌 Testing MT5 availability...")
    
    try:
        import MetaTrader5 as mt5
        print("   ✅ MetaTrader5 module imported")
        
        # Try to get version info (this works even without connection)
        version = mt5.version()
        if version:
            print(f"   📊 MT5 version: {version}")
        
        return True
        
    except ImportError:
        print("   ❌ MetaTrader5 module not available")
        print("   💡 This is expected if not running on Windows with MT5 installed")
        return False
    except Exception as e:
        print(f"   ⚠️  MT5 test warning: {e}")
        return True

def test_connection_class():
    """Test MT5 connection class (without actually connecting)"""
    print("🔗 Testing connection class...")
    
    try:
        from mt.core.connection import MT5Connection
        
        # Create connection instance
        connection = MT5Connection()
        print("   ✅ Connection class created")
        
        # Test properties (these shouldn't fail)
        print(f"   📊 Connection status: {'Connected' if connection.is_connected else 'Not connected'}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Connection class test failed: {e}")
        return False

def test_trader_class():
    """Test MT5 trader class"""
    print("🤖 Testing trader class...")
    
    try:
        from mt.core.connection import MT5Connection
        from mt.core.trader import MT5Trader
        
        # Create connection and trader
        connection = MT5Connection()
        trader = MT5Trader(connection)
        print("   ✅ Trader class created")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Trader class test failed: {e}")
        return False

def test_llm_client():
    """Test LLM client class"""
    print("🧠 Testing LLM client...")
    
    try:
        from mt.core.llm_client import LLMClient
        
        # Create LLM client
        llm_client = LLMClient()
        print("   ✅ LLM client created")
        
        # Test if it should request analysis (this is safe to test)
        should_request = llm_client.should_request_analysis()
        print(f"   📊 Should request analysis: {should_request}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ LLM client test failed: {e}")
        return False

def test_data_types():
    """Test trading signal data types"""
    print("📊 Testing data types...")
    
    try:
        from mt.core.trader import TradingSignal, SignalType, SignalStrength
        from datetime import datetime
        
        # Create a test signal
        signal = TradingSignal(
            symbol="EURUSD",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=0.75,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
            reasoning="Test signal",
            timestamp=datetime.now()
        )
        
        print("   ✅ TradingSignal created successfully")
        print(f"   📊 Test signal: {signal.symbol} {signal.signal_type.value} @ {signal.confidence}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Data types test failed: {e}")
        return False

def test_logging():
    """Test logging setup"""
    print("📝 Testing logging...")
    
    try:
        from mt.logger import setup_logging, get_logger
        
        # Setup logging
        setup_logging(
            level="INFO",
            console_output=True,
            file_output=False  # Don't create files during testing
        )
        
        # Get a logger and test it
        logger = get_logger("test")
        logger.info("Test log message")
        print("   ✅ Logging setup successful")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Logging test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("🚀 MT5 TRADING SYSTEM - QUICK TEST")
    print("=" * 60)
    print()
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_configuration), 
        ("MT5 Availability", test_mt5_availability),
        ("Connection Class", test_connection_class),
        ("Trader Class", test_trader_class),
        ("LLM Client", test_llm_client),
        ("Data Types", test_data_types),
        ("Logging", test_logging),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test_name} crashed: {e}")
            failed += 1
        print()
    
    # Summary
    print("=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total:  {passed + failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed! System looks good.")
        print("💡 Next steps:")
        print("   1. Update your MT5 credentials in configuration")
        print("   2. Run: python mt/example_usage.py")
        print("   3. Start API service: python mt5_api_service.py")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please fix these issues before proceeding.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
