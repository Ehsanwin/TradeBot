#!/usr/bin/env python3
"""
MT5 Trading System Configuration Template
Create your configuration by modifying the values below
"""

import os

# MT5 CONNECTION SETTINGS
# Update these with your actual MT5 account details
MT5_CONFIG = {
    # Your MT5 account login number
    "LOGIN": 12345678,
    
    # Your MT5 account password  
    "PASSWORD": "your_password_here",
    
    # Your MT5 broker server name (e.g., "MetaQuotes-Demo", "ICMarkets-Live01")
    "SERVER": "MetaQuotes-Demo",
    
    # Path to MT5 terminal (leave empty for auto-detection)
    "PATH": "",
    
    # Connection timeout in milliseconds
    "TIMEOUT": 30000,
    
    # Connection retry settings
    "RETRIES": 3,
    "RETRY_DELAY": 5,
}

# TRADING SETTINGS
TRADING_CONFIG = {
    # Magic number for identifying your trades (make this unique)
    "MAGIC_NUMBER": 234001,
    
    # Default symbols to trade
    "DEFAULT_SYMBOLS": ["XAUUSD", "EURUSD", "GBPUSD"],
    
    # Default trade volume
    "DEFAULT_VOLUME": 0.01,
    
    # Risk management settings
    "MAX_SLIPPAGE": 20,
    "MAX_SPREAD": 50,
    "MAX_RISK_PERCENT": 2.0,
    "MIN_RISK_REWARD": 1.5,
    "MAX_POSITIONS": 3,
    "MAX_DAILY_LOSS": 5.0,
}

# LLM INTEGRATION SETTINGS
LLM_CONFIG = {
    # LLM API service URL
    "API_BASE_URL": "http://localhost:5001",
    
    # Analysis intervals in minutes
    "ANALYSIS_INTERVAL_MINUTES": 15,
    "SIGNAL_EXPIRY_MINUTES": 60,
    
    # Signal confidence threshold (0.0 to 1.0)
    "MIN_CONFIDENCE_THRESHOLD": 0.7,
    
    # Allowed signal types
    "ALLOWED_SIGNAL_TYPES": ["BUY", "SELL"],
    
    # API timeout settings
    "TIMEOUT": 30,
    "RETRIES": 3,
}

# SYSTEM SETTINGS
SYSTEM_CONFIG = {
    # Enable/disable the trading system
    "ENABLED": True,
    
    # Debug mode (more detailed logging)
    "DEBUG": False,
    
    # Dry run mode (no actual trades, just simulate)
    "DRY_RUN": True,  # Set to False for live trading
    
    # Auto trading enabled
    "AUTO_TRADE": True,
    
    # Logging level (DEBUG, INFO, WARNING, ERROR)
    "LOG_LEVEL": "INFO",
    
    # Environment type
    "ENVIRONMENT": "development",
    
    # Health check interval in seconds
    "HEALTH_CHECK_INTERVAL": 60,
}

# API SERVICE SETTINGS
API_CONFIG = {
    # Port for local MT5 API service
    "PORT": 8001,
    
    # Enable API service
    "ENABLED": True,
}

def setup_environment_variables():
    """
    Set environment variables from configuration
    This is useful for testing or when you can't create .env files
    """
    # MT5 Connection
    os.environ["MT5_LOGIN"] = str(MT5_CONFIG["LOGIN"])
    os.environ["MT5_PASSWORD"] = MT5_CONFIG["PASSWORD"]
    os.environ["MT5_SERVER"] = MT5_CONFIG["SERVER"]
    os.environ["MT5_PATH"] = MT5_CONFIG["PATH"]
    
    # Trading
    os.environ["MT5_MAGIC_NUMBER"] = str(TRADING_CONFIG["MAGIC_NUMBER"])
    os.environ["MT5_DEFAULT_SYMBOLS"] = ",".join(TRADING_CONFIG["DEFAULT_SYMBOLS"])
    os.environ["MT5_DEFAULT_VOLUME"] = str(TRADING_CONFIG["DEFAULT_VOLUME"])
    os.environ["MT5_MAX_SLIPPAGE"] = str(TRADING_CONFIG["MAX_SLIPPAGE"])
    os.environ["MT5_MAX_SPREAD"] = str(TRADING_CONFIG["MAX_SPREAD"])
    os.environ["MT5_MAX_RISK_PERCENT"] = str(TRADING_CONFIG["MAX_RISK_PERCENT"])
    os.environ["MT5_MIN_RISK_REWARD"] = str(TRADING_CONFIG["MIN_RISK_REWARD"])
    os.environ["MT5_MAX_POSITIONS"] = str(TRADING_CONFIG["MAX_POSITIONS"])
    
    # LLM Integration
    os.environ["LLM_API_BASE_URL"] = LLM_CONFIG["API_BASE_URL"]
    os.environ["LLM_ANALYSIS_INTERVAL_MINUTES"] = str(LLM_CONFIG["ANALYSIS_INTERVAL_MINUTES"])
    os.environ["LLM_SIGNAL_EXPIRY_MINUTES"] = str(LLM_CONFIG["SIGNAL_EXPIRY_MINUTES"])
    os.environ["LLM_MIN_CONFIDENCE_THRESHOLD"] = str(LLM_CONFIG["MIN_CONFIDENCE_THRESHOLD"])
    
    # System Settings
    os.environ["MT5_ENABLED"] = str(SYSTEM_CONFIG["ENABLED"]).lower()
    os.environ["MT5_DEBUG"] = str(SYSTEM_CONFIG["DEBUG"]).lower()
    os.environ["MT5_DRY_RUN"] = str(SYSTEM_CONFIG["DRY_RUN"]).lower()
    os.environ["MT5_AUTO_TRADE"] = str(SYSTEM_CONFIG["AUTO_TRADE"]).lower()
    os.environ["MT5_LOG_LEVEL"] = SYSTEM_CONFIG["LOG_LEVEL"]
    os.environ["ENVIRONMENT"] = SYSTEM_CONFIG["ENVIRONMENT"]

def create_env_file():
    """
    Create a .env file from the configuration
    """
    env_content = f"""# MT5 Trading System Environment Configuration
# Generated from config_template.py

# MT5 CONNECTION SETTINGS
MT5_LOGIN={MT5_CONFIG["LOGIN"]}
MT5_PASSWORD={MT5_CONFIG["PASSWORD"]}
MT5_SERVER={MT5_CONFIG["SERVER"]}
MT5_PATH={MT5_CONFIG["PATH"]}
MT5_CONNECTION_TIMEOUT={MT5_CONFIG["TIMEOUT"]}
MT5_CONNECTION_RETRIES={MT5_CONFIG["RETRIES"]}
MT5_RETRY_DELAY={MT5_CONFIG["RETRY_DELAY"]}

# TRADING SETTINGS
MT5_MAGIC_NUMBER={TRADING_CONFIG["MAGIC_NUMBER"]}
MT5_DEFAULT_SYMBOLS={",".join(TRADING_CONFIG["DEFAULT_SYMBOLS"])}
MT5_DEFAULT_VOLUME={TRADING_CONFIG["DEFAULT_VOLUME"]}
MT5_MAX_SLIPPAGE={TRADING_CONFIG["MAX_SLIPPAGE"]}
MT5_MAX_SPREAD={TRADING_CONFIG["MAX_SPREAD"]}
MT5_MAX_RISK_PERCENT={TRADING_CONFIG["MAX_RISK_PERCENT"]}
MT5_MIN_RISK_REWARD={TRADING_CONFIG["MIN_RISK_REWARD"]}
MT5_MAX_POSITIONS={TRADING_CONFIG["MAX_POSITIONS"]}
MT5_MAX_DAILY_LOSS={TRADING_CONFIG["MAX_DAILY_LOSS"]}

# LLM INTEGRATION
LLM_API_BASE_URL={LLM_CONFIG["API_BASE_URL"]}
LLM_ANALYSIS_INTERVAL_MINUTES={LLM_CONFIG["ANALYSIS_INTERVAL_MINUTES"]}
LLM_SIGNAL_EXPIRY_MINUTES={LLM_CONFIG["SIGNAL_EXPIRY_MINUTES"]}
LLM_MIN_CONFIDENCE_THRESHOLD={LLM_CONFIG["MIN_CONFIDENCE_THRESHOLD"]}

# SYSTEM SETTINGS
MT5_ENABLED={str(SYSTEM_CONFIG["ENABLED"]).lower()}
MT5_DEBUG={str(SYSTEM_CONFIG["DEBUG"]).lower()}
MT5_DRY_RUN={str(SYSTEM_CONFIG["DRY_RUN"]).lower()}
MT5_AUTO_TRADE={str(SYSTEM_CONFIG["AUTO_TRADE"]).lower()}
MT5_LOG_LEVEL={SYSTEM_CONFIG["LOG_LEVEL"]}
ENVIRONMENT={SYSTEM_CONFIG["ENVIRONMENT"]}
MT5_HEALTH_CHECK_INTERVAL={SYSTEM_CONFIG["HEALTH_CHECK_INTERVAL"]}

# API SERVICE SETTINGS
MT5_API_PORT={API_CONFIG["PORT"]}
MT5_API_ENABLED={str(API_CONFIG["ENABLED"]).lower()}
"""
    
    env_file_path = os.path.join(os.path.dirname(__file__), '.env')
    
    try:
        with open(env_file_path, 'w') as f:
            f.write(env_content)
        print(f"✅ Environment file created: {env_file_path}")
        print("⚠️  Remember to update the MT5 credentials in the .env file!")
        return env_file_path
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return None

def print_configuration_summary():
    """Print configuration summary for verification"""
    print("\n" + "="*60)
    print("MT5 TRADING SYSTEM CONFIGURATION SUMMARY")
    print("="*60)
    
    print(f"\n🔌 MT5 CONNECTION:")
    print(f"   Login: {MT5_CONFIG['LOGIN']}")
    print(f"   Server: {MT5_CONFIG['SERVER']}")
    print(f"   Password: {'*' * len(str(MT5_CONFIG['PASSWORD']))}")
    
    print(f"\n📈 TRADING SETTINGS:")
    print(f"   Magic Number: {TRADING_CONFIG['MAGIC_NUMBER']}")
    print(f"   Default Symbols: {', '.join(TRADING_CONFIG['DEFAULT_SYMBOLS'])}")
    print(f"   Default Volume: {TRADING_CONFIG['DEFAULT_VOLUME']}")
    print(f"   Max Risk: {TRADING_CONFIG['MAX_RISK_PERCENT']}%")
    print(f"   Max Positions: {TRADING_CONFIG['MAX_POSITIONS']}")
    
    print(f"\n🤖 LLM INTEGRATION:")
    print(f"   API URL: {LLM_CONFIG['API_BASE_URL']}")
    print(f"   Analysis Interval: {LLM_CONFIG['ANALYSIS_INTERVAL_MINUTES']} minutes")
    print(f"   Confidence Threshold: {LLM_CONFIG['MIN_CONFIDENCE_THRESHOLD']}")
    
    print(f"\n⚙️  SYSTEM SETTINGS:")
    print(f"   Enabled: {'✅' if SYSTEM_CONFIG['ENABLED'] else '❌'}")
    print(f"   Dry Run: {'✅' if SYSTEM_CONFIG['DRY_RUN'] else '❌'}")
    print(f"   Debug Mode: {'✅' if SYSTEM_CONFIG['DEBUG'] else '❌'}")
    print(f"   Log Level: {SYSTEM_CONFIG['LOG_LEVEL']}")
    
    print("\n" + "="*60)
    
    if SYSTEM_CONFIG['DRY_RUN']:
        print("⚠️  DRY RUN MODE IS ENABLED - No actual trades will be executed")
    else:
        print("🚨 LIVE TRADING MODE - Real trades will be executed!")
        
    print("="*60)

if __name__ == "__main__":
    print("🚀 MT5 Trading System Configuration")
    print_configuration_summary()
    
    print("\nChoose an option:")
    print("1. Setup environment variables (for current session)")
    print("2. Create .env file (recommended)")
    print("3. Just show configuration")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        setup_environment_variables()
        print("✅ Environment variables set for current session")
    elif choice == "2":
        create_env_file()
    elif choice == "3":
        print("Configuration displayed above")
    else:
        print("Invalid choice")
