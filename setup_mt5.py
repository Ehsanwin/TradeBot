#!/usr/bin/env python3
"""
MT5 Trading System Setup Script

This script helps you set up and configure the MT5 trading system.
It will:
1. Check for required dependencies
2. Create configuration files
3. Test MT5 connection
4. Verify LLM integration
5. Run basic functionality tests

Usage:
    python setup_mt5.py
"""

import os
import sys
import subprocess
from pathlib import Path
import importlib.util

def print_banner():
    """Print setup banner"""
    print("=" * 60)
    print("🚀 MT5 TRADING SYSTEM SETUP")
    print("=" * 60)
    print()

def check_python_version():
    """Check if Python version is compatible"""
    print("🐍 Checking Python version...")
    
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    
    print(f"✅ Python {sys.version.split()[0]} - Compatible")
    return True

def check_windows():
    """Check if running on Windows (required for MT5)"""
    print("🖥️  Checking operating system...")
    
    if os.name != 'nt':
        print("❌ This system requires Windows to access MetaTrader5")
        print("   You can use the Docker API client on other systems")
        return False
    
    print("✅ Windows detected - MT5 compatible")
    return True

def check_dependencies():
    """Check for required Python packages"""
    print("📦 Checking dependencies...")
    
    required_packages = [
        'MetaTrader5',
        'fastapi', 
        'uvicorn',
        'pydantic',
        'requests',
        'python-dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package.replace('-', '_'))
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} - Missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing {len(missing_packages)} required packages")
        print("📥 To install missing packages, run:")
        print(f"   pip install -r requirements_local_mt5.txt")
        return False
    
    print("✅ All dependencies are installed")
    return True

def install_dependencies():
    """Install missing dependencies"""
    requirements_file = "requirements_local_mt5.txt"
    
    if not os.path.exists(requirements_file):
        print(f"❌ Requirements file not found: {requirements_file}")
        return False
    
    print("📥 Installing dependencies...")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "-r", requirements_file
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Dependencies installed successfully")
            return True
        else:
            print(f"❌ Failed to install dependencies: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def setup_configuration():
    """Setup MT5 configuration"""
    print("⚙️  Setting up configuration...")
    
    # Check if config template exists
    config_template_path = "mt/config_template.py"
    
    if not os.path.exists(config_template_path):
        print(f"❌ Configuration template not found: {config_template_path}")
        return False
    
    # Import and run configuration
    try:
        sys.path.insert(0, os.path.dirname(config_template_path))
        
        print("\n📋 Current configuration:")
        print("Please review and update the MT5 credentials in the configuration")
        
        # Run configuration setup
        from mt.config_template import print_configuration_summary, create_env_file
        print_configuration_summary()
        
        # Ask user if they want to create .env file
        choice = input("\n❓ Create .env file with current configuration? (y/n): ").lower().strip()
        
        if choice in ['y', 'yes']:
            env_file = create_env_file()
            if env_file:
                print("✅ Configuration file created")
                print("⚠️  Remember to update your MT5 credentials in the .env file!")
                return True
        
        print("⚠️  Configuration not saved - you'll need to set environment variables manually")
        return False
        
    except Exception as e:
        print(f"❌ Error setting up configuration: {e}")
        return False

def test_mt5_connection():
    """Test MT5 connection"""
    print("🔌 Testing MT5 connection...")
    
    try:
        # Check if we can import MT5
        import MetaTrader5 as mt5
        
        # Try to initialize (this will fail without proper credentials)
        if mt5.initialize():
            account_info = mt5.account_info()
            if account_info:
                print(f"✅ MT5 connected successfully")
                print(f"   Account: {account_info.login}")
                print(f"   Server: {account_info.server}")
                print(f"   Balance: {account_info.balance} {account_info.currency}")
                mt5.shutdown()
                return True
            else:
                mt5.shutdown()
        
        print("⚠️  MT5 initialization failed - likely due to missing credentials")
        print("   Update your MT5 login details in the configuration")
        return False
        
    except Exception as e:
        print(f"❌ MT5 connection test failed: {e}")
        return False

def test_system_components():
    """Test system components"""
    print("🧪 Testing system components...")
    
    try:
        # Test imports
        sys.path.insert(0, 'mt')
        
        from mt.logger import setup_logging, get_logger
        from mt.config.settings import get_mt5_settings, validate_settings
        
        # Setup basic logging for testing
        setup_logging(level="INFO", console_output=True, file_output=False)
        logger = get_logger("setup_test")
        
        # Test settings validation
        is_valid, error_msg = validate_settings()
        if is_valid:
            print("✅ Settings validation passed")
        else:
            print(f"⚠️  Settings validation issues: {error_msg}")
        
        # Test settings loading
        settings = get_mt5_settings()
        print("✅ Settings loaded successfully")
        
        # Test connection class (without actually connecting)
        from mt.core.connection import MT5Connection
        connection = MT5Connection()
        print("✅ Connection class initialized")
        
        # Test trader class
        from mt.core.trader import MT5Trader
        trader = MT5Trader(connection)
        print("✅ Trader class initialized")
        
        # Test LLM client
        from mt.core.llm_client import LLMClient
        llm_client = LLMClient()
        print("✅ LLM client initialized")
        
        return True
        
    except Exception as e:
        print(f"❌ Component test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_directories():
    """Create necessary directories"""
    print("📁 Creating directories...")
    
    directories = [
        "logs",
        "mt/logs"
    ]
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"   ✅ {directory}")
        except Exception as e:
            print(f"   ❌ Failed to create {directory}: {e}")
            return False
    
    return True

def print_next_steps():
    """Print next steps for the user"""
    print("\n" + "=" * 60)
    print("🎉 SETUP COMPLETE!")
    print("=" * 60)
    
    print("\n📋 NEXT STEPS:")
    print("1. Update your MT5 credentials in mt/.env file:")
    print("   - MT5_LOGIN: Your account number") 
    print("   - MT5_PASSWORD: Your account password")
    print("   - MT5_SERVER: Your broker's server name")
    
    print("\n2. Test your setup:")
    print("   python mt/example_usage.py")
    
    print("\n3. Start the MT5 API service:")
    print("   python mt5_api_service.py")
    
    print("\n4. Run the main trading system:")
    print("   python mt/main.py --dry-run --once")
    
    print("\n⚠️  IMPORTANT REMINDERS:")
    print("   - Start with DRY RUN mode to test without real trades")
    print("   - Make sure MT5 terminal is running and logged in")
    print("   - Verify your risk management settings")
    print("   - Test with small amounts first")
    
    print("\n📚 DOCUMENTATION:")
    print("   - Check mt/README.md for detailed usage")
    print("   - Review configuration in mt/config_template.py")
    print("   - Log files are saved in logs/ directory")
    
    print("\n" + "=" * 60)

def main():
    """Main setup function"""
    print_banner()
    
    # Check system requirements
    if not check_python_version():
        sys.exit(1)
    
    if not check_windows():
        print("⚠️  Continuing setup for API client mode only")
    
    # Check and install dependencies
    if not check_dependencies():
        choice = input("📥 Install missing dependencies? (y/n): ").lower().strip()
        if choice in ['y', 'yes']:
            if not install_dependencies():
                sys.exit(1)
            # Re-check after installation
            if not check_dependencies():
                sys.exit(1)
        else:
            print("❌ Dependencies required - setup aborted")
            sys.exit(1)
    
    # Create directories
    if not create_directories():
        print("⚠️  Some directories could not be created")
    
    # Setup configuration
    if not setup_configuration():
        print("⚠️  Configuration setup incomplete")
    
    # Test system components
    if not test_system_components():
        print("❌ System component tests failed")
        sys.exit(1)
    
    # Test MT5 connection (optional)
    test_mt5_connection()  # Don't fail setup if this fails
    
    # Print next steps
    print_next_steps()

if __name__ == "__main__":
    main()
