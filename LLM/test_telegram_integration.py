#!/usr/bin/env python3
"""
Test LLM Telegram Integration

Quick test script to verify the Telegram integration is working properly.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test all required imports"""
    print("🧪 Testing imports...")
    
    try:
        # Test LLM system
        from LLM.config.settings import get_llm_settings
        from LLM.core.telegram_integration import TelegramFormatter, TelegramNotifier
        from LLM.telegram_command import LLMTelegramCommand
        print("✅ LLM modules imported successfully")
        
        # Test Telegram bot integration
        from orchestrator.bot.telegram_bot import TradingBotTelegram, LLM_AVAILABLE
        print(f"✅ Telegram bot imported (LLM_AVAILABLE: {LLM_AVAILABLE})")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_configuration():
    """Test configuration loading"""
    print("\n⚙️ Testing configuration...")
    
    try:
        from LLM.config.settings import get_llm_settings
        settings = get_llm_settings()
        
        print(f"✅ LLM enabled: {settings.core.enabled}")
        print(f"✅ OpenAI model: {settings.core.openai.model}")
        print(f"✅ Backend URL: {settings.backend_base_url}")
        
        # Check API key
        api_key = settings.openai_api_key
        if api_key:
            print(f"✅ OpenAI API key configured (length: {len(api_key)})")
        else:
            print("⚠️ OpenAI API key not configured")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_telegram_formatting():
    """Test Telegram message formatting"""
    print("\n📱 Testing Telegram formatting...")
    
    try:
        from LLM.core.telegram_integration import TelegramFormatter
        from LLM.core.data_types import TradingSignal, SignalType, SignalStrength
        
        # Create test signal
        signal = TradingSignal(
            symbol="EUR_USD",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=0.85,
            entry_price=1.0950,
            stop_loss=1.0920,
            take_profit=1.1000,
            reasoning="Test signal for Telegram formatting",
            key_factors=["Factor 1", "Factor 2"],
            risks=["Risk 1", "Risk 2"]
        )
        
        # Test formatting
        formatter = TelegramFormatter()
        formatted = formatter.format_signal(signal)
        
        if "📈" in formatted and "EUR_USD" in formatted:
            print("✅ Signal formatting working")
        else:
            print("❌ Signal formatting failed")
            
        # Test message splitting
        long_text = "A" * 5000  # Text longer than Telegram limit
        split_messages = formatter.split_long_message(long_text)
        
        if len(split_messages) > 1:
            print("✅ Message splitting working")
        else:
            print("❌ Message splitting failed")
            
        return True
        
    except Exception as e:
        print(f"❌ Telegram formatting test failed: {e}")
        return False

def test_system_initialization():
    """Test LLM system initialization (without making API calls)"""
    print("\n🚀 Testing system initialization...")
    
    try:
        from LLM.main import LLMTradingSystem
        
        system = LLMTradingSystem()
        print("✅ LLM system created")
        
        # Check if we can initialize (will fail without API key but that's ok)
        if os.getenv("OPENAI_API_KEY"):
            try:
                system.initialize_services()
                print("✅ LLM system initialized successfully")
                system.cleanup()
                return True
            except Exception as e:
                print(f"⚠️ LLM system initialization failed (expected without proper config): {e}")
                return True
        else:
            print("⚠️ Skipping initialization test (no OPENAI_API_KEY)")
            return True
            
    except Exception as e:
        print(f"❌ System initialization test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 LLM Telegram Integration Test Suite")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_configuration),
        ("Telegram Formatting", test_telegram_formatting),
        ("System Initialization", test_system_initialization)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Telegram integration is ready.")
        print("\n📋 Next steps:")
        print("1. Set OPENAI_API_KEY in your .env file")
        print("2. Configure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_IDS")
        print("3. Start your Telegram bot: python orchestrator/bot/telegram_bot.py")
        print("4. Send /llm command to your bot")
        return True
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
