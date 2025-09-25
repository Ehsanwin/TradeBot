#!/usr/bin/env python3
"""
MT5 Trading System Startup Script

This script provides an easy way to start the complete MT5 trading system
with proper initialization, health checks, and monitoring.

Usage:
    python start_mt5_system.py [options]
"""

import argparse
import os
import sys
import time
import subprocess
from pathlib import Path
import signal
import threading

def print_banner():
    """Print startup banner"""
    print("=" * 70)
    print("🚀 MT5 TRADING SYSTEM STARTUP")
    print("=" * 70)
    print()

def print_status(message, status="info"):
    """Print colored status message"""
    icons = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}
    print(f"{icons.get(status, 'ℹ️')} {message}")

def check_requirements():
    """Check system requirements"""
    print_status("Checking system requirements...", "info")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print_status(f"Python 3.8+ required. Current: {sys.version.split()[0]}", "error")
        return False
    
    print_status(f"Python {sys.version.split()[0]} - OK", "success")
    
    # Check if on Windows (for MT5)
    if os.name != 'nt':
        print_status("Not running on Windows - API mode only", "warning")
    else:
        print_status("Windows detected - Full MT5 support available", "success")
    
    # Check required files
    required_files = [
        "mt/main.py",
        "mt5_api_service.py", 
        "requirements_local_mt5.txt"
    ]
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            print_status(f"Required file missing: {file_path}", "error")
            return False
    
    print_status("All required files found", "success")
    
    # Check dependencies
    try:
        import MetaTrader5
        print_status("MetaTrader5 module - OK", "success")
    except ImportError:
        if os.name == 'nt':
            print_status("MetaTrader5 module missing on Windows", "error")
            return False
        else:
            print_status("MetaTrader5 not available - API mode only", "warning")
    
    return True

def check_configuration():
    """Check configuration"""
    print_status("Checking configuration...", "info")
    
    config_files = [
        "mt/.env",
        "mt/config_template.py"
    ]
    
    config_found = False
    for config_file in config_files:
        if os.path.exists(config_file):
            print_status(f"Configuration found: {config_file}", "success")
            config_found = True
            break
    
    if not config_found:
        print_status("No configuration file found", "warning")
        print_status("Run: python mt/config_template.py to create one", "info")
        return False
    
    # Test configuration loading
    try:
        sys.path.insert(0, 'mt')
        from mt.config.settings import get_mt5_settings, validate_settings
        
        settings = get_mt5_settings()
        is_valid, error_msg = validate_settings()
        
        if is_valid:
            print_status("Configuration validation - OK", "success")
            print_status(f"Trading mode: {'DRY RUN' if settings.core.dry_run else 'LIVE'}", 
                        "warning" if not settings.core.dry_run else "info")
        else:
            print_status(f"Configuration issues: {error_msg}", "warning")
        
        return True
        
    except Exception as e:
        print_status(f"Configuration error: {e}", "error")
        return False

def install_dependencies():
    """Install missing dependencies"""
    print_status("Installing dependencies...", "info")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "-r", "requirements_local_mt5.txt"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print_status("Dependencies installed successfully", "success")
            return True
        else:
            print_status(f"Failed to install dependencies: {result.stderr}", "error")
            return False
            
    except Exception as e:
        print_status(f"Error installing dependencies: {e}", "error")
        return False

def start_api_service(background=True):
    """Start MT5 API service"""
    print_status("Starting MT5 API service...", "info")
    
    try:
        if background:
            # Start as background process
            process = subprocess.Popen([
                sys.executable, "mt5_api_service.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait a moment to see if it starts successfully
            time.sleep(2)
            
            if process.poll() is None:
                print_status("API service started in background", "success")
                print_status("API available at: http://localhost:8001", "info")
                return process
            else:
                stdout, stderr = process.communicate()
                print_status(f"API service failed to start: {stderr.decode()}", "error")
                return None
        else:
            # Start in foreground
            result = subprocess.run([sys.executable, "mt5_api_service.py"])
            return result
            
    except Exception as e:
        print_status(f"Error starting API service: {e}", "error")
        return None

def start_trading_system(args):
    """Start the main trading system"""
    print_status("Starting MT5 trading system...", "info")
    
    try:
        cmd = [sys.executable, "mt/main.py"]
        
        # Add command line arguments
        if args.dry_run:
            cmd.append("--dry-run")
        if args.once:
            cmd.append("--once") 
        if args.debug:
            cmd.append("--debug")
        if args.symbols:
            cmd.extend(["--symbols", args.symbols])
        
        print_status(f"Command: {' '.join(cmd)}", "info")
        
        # Start trading system
        result = subprocess.run(cmd)
        return result.returncode == 0
        
    except KeyboardInterrupt:
        print_status("Trading system interrupted by user", "warning")
        return True
    except Exception as e:
        print_status(f"Error starting trading system: {e}", "error")
        return False

def monitor_services(api_process):
    """Monitor background services"""
    print_status("Starting service monitor...", "info")
    
    def check_api_service():
        if api_process and api_process.poll() is not None:
            print_status("API service stopped unexpectedly", "warning")
            return False
        return True
    
    def monitor_loop():
        while True:
            time.sleep(30)  # Check every 30 seconds
            
            if not check_api_service():
                print_status("Attempting to restart API service...", "warning")
                # Could implement restart logic here
            
            # Check system health
            try:
                import requests
                response = requests.get("http://localhost:8001/health", timeout=5)
                if response.status_code != 200:
                    print_status("API service health check failed", "warning")
            except:
                pass  # API might not be running
    
    # Start monitor in background thread
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()

def signal_handler(signum, frame, processes):
    """Handle shutdown signals"""
    print_status(f"Received signal {signum}, shutting down...", "warning")
    
    # Stop background processes
    for proc in processes:
        if proc and proc.poll() is None:
            proc.terminate()
    
    sys.exit(0)

def main():
    """Main startup function"""
    parser = argparse.ArgumentParser(description="MT5 Trading System Startup")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Enable dry run mode (no real trades)")
    parser.add_argument("--once", action="store_true", 
                       help="Run once and exit")
    parser.add_argument("--debug", action="store_true", 
                       help="Enable debug logging")
    parser.add_argument("--symbols", type=str, 
                       help="Comma-separated symbols to trade")
    parser.add_argument("--api-only", action="store_true", 
                       help="Start only API service")
    parser.add_argument("--no-api", action="store_true", 
                       help="Skip API service startup")
    parser.add_argument("--install-deps", action="store_true", 
                       help="Install dependencies before starting")
    parser.add_argument("--skip-checks", action="store_true", 
                       help="Skip system requirement checks")
    
    args = parser.parse_args()
    
    print_banner()
    
    # System checks
    if not args.skip_checks:
        if not check_requirements():
            print_status("System requirements not met", "error")
            sys.exit(1)
        
        if not check_configuration():
            print_status("Configuration issues detected", "error")
            choice = input("Continue anyway? (y/n): ").lower()
            if choice not in ['y', 'yes']:
                sys.exit(1)
    
    # Install dependencies if requested
    if args.install_deps:
        if not install_dependencies():
            sys.exit(1)
    
    # Start services
    processes = []
    
    try:
        # Start API service (unless disabled)
        api_process = None
        if not args.no_api and not args.once:
            api_process = start_api_service(background=True)
            if api_process:
                processes.append(api_process)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, lambda s, f: signal_handler(s, f, processes))
        signal.signal(signal.SIGTERM, lambda s, f: signal_handler(s, f, processes))
        
        # API only mode
        if args.api_only:
            print_status("API-only mode - API service running", "success")
            print_status("Press Ctrl+C to stop", "info")
            
            # Keep running until interrupted
            while True:
                time.sleep(1)
        
        # Start monitoring (for background services)
        if processes:
            monitor_services(api_process)
        
        # Start main trading system
        print_status("System initialization complete", "success")
        print()
        
        if start_trading_system(args):
            print_status("Trading system completed successfully", "success")
        else:
            print_status("Trading system encountered errors", "error")
            
    except KeyboardInterrupt:
        print_status("Startup interrupted by user", "warning")
    except Exception as e:
        print_status(f"Startup error: {e}", "error")
    finally:
        # Cleanup
        print_status("Shutting down services...", "info")
        for proc in processes:
            if proc and proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=5)
        
        print_status("Shutdown complete", "success")

if __name__ == "__main__":
    main()
