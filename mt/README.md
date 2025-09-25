# MT5 Trading System

A comprehensive MetaTrader5 trading system with LLM-powered signal generation, automated trade execution, and robust risk management.

## 🎯 Features

- **MT5 Integration**: Direct connection to MetaTrader5 terminal
- **LLM-Powered Signals**: AI-generated trading signals with confidence scoring
- **Risk Management**: Built-in position sizing and risk controls
- **Real-time Trading**: Automated trade execution and monitoring
- **API Service**: REST API for Docker/remote integration
- **Comprehensive Logging**: Detailed logging and error handling
- **Dry Run Mode**: Test strategies without real money

## 📋 Requirements

### System Requirements
- **Windows 10/11** (for MT5 integration)
- **Python 3.8+**
- **MetaTrader5 Terminal** installed and configured

### MT5 Setup
1. Install MetaTrader5 from your broker
2. Create a trading account (demo recommended for testing)
3. Ensure "Allow automated trading" is enabled in MT5
4. Note your account login, password, and server name

## 🚀 Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements_local_mt5.txt

# Run setup script
python setup_mt5.py
```

### 2. Configuration

The setup script will help you create configuration files. Alternatively:

```python
# Edit mt/config_template.py with your settings
python mt/config_template.py
```

**Required Settings:**
- `MT5_LOGIN`: Your MT5 account number
- `MT5_PASSWORD`: Your MT5 account password  
- `MT5_SERVER`: Your broker's server name
- `MT5_DRY_RUN`: Set to `true` for testing, `false` for live trading

### 3. Test Your Setup

```bash
# Run system tests
python mt/test_mt5.py

# Test with example usage
python mt/example_usage.py
```

### 4. Start Trading

```bash
# Start with dry run mode (recommended)
python mt/main.py --dry-run --once

# Run continuously (still dry run)
python mt/main.py --dry-run

# For live trading (remove --dry-run when ready)
python mt/main.py
```

## 📚 Usage Examples

### Basic Usage

```python
from mt.core.connection import MT5Connection
from mt.core.trader import MT5Trader
from mt.core.llm_client import LLMClient

# Create connection
with MT5Connection() as connection:
    if connection.is_connected:
        # Initialize trader
        trader = MT5Trader(connection)
        
        # Get account info
        account = connection.get_account_info()
        print(f"Balance: {account['balance']}")
        
        # Get LLM signals
        llm_client = LLMClient()
        signals = llm_client.get_trading_signals(["EURUSD", "GBPUSD"])
        
        # Execute signals
        for signal in signals:
            result = trader.execute_signal(signal)
            print(f"Trade result: {result.result.value}")
```

### API Service

```bash
# Start local API service
python mt5_api_service.py

# API will be available at http://localhost:8001
```

API endpoints:
- `GET /health` - Health check
- `POST /connect` - Connect to MT5
- `POST /execute_trade` - Execute trade
- `GET /positions` - Get open positions
- `GET /account_info` - Account information

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the `mt/` directory:

```bash
# MT5 Connection
MT5_LOGIN=12345678
MT5_PASSWORD=your_password
MT5_SERVER=MetaQuotes-Demo

# Trading Settings
MT5_DEFAULT_SYMBOLS=XAUUSD,EURUSD,GBPUSD
MT5_DEFAULT_VOLUME=0.01
MT5_MAX_RISK_PERCENT=2.0
MT5_MAX_POSITIONS=3

# LLM Integration
LLM_API_BASE_URL=http://localhost:5001
LLM_MIN_CONFIDENCE_THRESHOLD=0.7

# System Settings
MT5_ENABLED=true
MT5_DRY_RUN=true
MT5_DEBUG=false
```

### Configuration Options

| Setting | Description | Default |
|---------|-------------|---------|
| `MT5_LOGIN` | MT5 account login number | Required |
| `MT5_PASSWORD` | MT5 account password | Required |
| `MT5_SERVER` | Broker server name | Required |
| `MT5_DRY_RUN` | Enable dry run mode | `true` |
| `MT5_DEFAULT_VOLUME` | Default trade volume | `0.01` |
| `MT5_MAX_RISK_PERCENT` | Max risk per trade (%) | `2.0` |
| `MT5_MAX_POSITIONS` | Max concurrent positions | `3` |
| `LLM_MIN_CONFIDENCE_THRESHOLD` | Min signal confidence | `0.7` |

## 🛡️ Risk Management

### Built-in Protections

1. **Position Sizing**: Automatic calculation based on risk percentage
2. **Risk-Reward Ratios**: Enforces minimum risk-reward requirements
3. **Position Limits**: Maximum number of concurrent positions
4. **Stop Loss/Take Profit**: Automatic placement of protective orders
5. **Signal Validation**: Multiple validation checks before execution
6. **Dry Run Mode**: Test without real money

### Configuration

```python
TRADING_CONFIG = {
    "MAX_RISK_PERCENT": 2.0,      # Max 2% risk per trade
    "MIN_RISK_REWARD": 1.5,       # Minimum 1.5:1 reward ratio
    "MAX_POSITIONS": 3,           # Max 3 concurrent positions
    "MAX_DAILY_LOSS": 5.0,        # Max 5% daily loss
    "DEFAULT_VOLUME": 0.01        # Default position size
}
```

## 🔧 API Integration

### Local API Service

The system includes a REST API service for integration with Docker containers or remote systems:

```bash
# Start API service
python mt5_api_service.py

# Service runs on http://localhost:8001
```

### Docker Integration

```yaml
# docker-compose.yml
services:
  mt5_api:
    image: your_mt5_api_image
    ports:
      - "8001:8001"
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

## 📊 Monitoring & Logging

### Log Files
- `logs/mt5_trading.log` - Main trading log
- `logs/mt5_api_service.log` - API service log

### Log Levels
- `DEBUG` - Detailed debugging information
- `INFO` - General information (default)
- `WARNING` - Warning messages
- `ERROR` - Error messages

### Health Monitoring

```python
# Get trading summary
summary = trader.get_trading_summary()
print(f"Win Rate: {summary['win_rate_30d']}%")
print(f"Total Profit: {summary['total_profit_30d']}")
```

## 🐛 Troubleshooting

### Common Issues

**"MT5 initialization failed"**
- Ensure MT5 terminal is running
- Check account credentials
- Verify account allows automated trading

**"LLM service not available"**
- Ensure LLM service is running on configured URL
- Check LLM_API_BASE_URL setting

**"Symbol not available"**
- Verify symbol exists in MT5
- Check Market Watch window in MT5

**"Invalid signal confidence"**
- Lower LLM_MIN_CONFIDENCE_THRESHOLD
- Check LLM signal generation

### Debug Mode

```bash
# Enable debug logging
python mt/main.py --debug

# Or set in configuration
MT5_DEBUG=true
```

## 🧪 Testing

### Run Tests

```bash
# Quick system test
python mt/test_mt5.py

# Example usage test
python mt/example_usage.py

# Single cycle test
python mt/main.py --dry-run --once
```

### Dry Run Mode

Always test in dry run mode first:

```bash
# Test trading logic without real trades
MT5_DRY_RUN=true python mt/main.py
```

## 📈 Performance Tips

1. **Use appropriate timeframes** - Match analysis interval to trading strategy
2. **Monitor spreads** - Avoid trading during high spread periods
3. **Regular health checks** - Monitor system performance
4. **Optimize position sizing** - Adjust based on account size
5. **Review logs regularly** - Check for errors or warnings

## 🚨 Safety Guidelines

### Before Live Trading

1. ✅ Test thoroughly in dry run mode
2. ✅ Start with small position sizes
3. ✅ Use demo account first
4. ✅ Verify all stop losses work
5. ✅ Monitor system continuously
6. ✅ Have manual override ready

### Risk Warnings

- **Never risk more than you can afford to lose**
- **Past performance doesn't guarantee future results**
- **Algorithmic trading carries risks**
- **Always monitor your positions**
- **Have adequate funds for margin calls**

## 📞 Support

### Getting Help

1. Check this README first
2. Review log files for errors
3. Run diagnostic tests
4. Check configuration settings

### Useful Commands

```bash
# System diagnostics
python mt/test_mt5.py

# Configuration check
python mt/config_template.py

# View logs
tail -f logs/mt5_trading.log

# API health check
curl http://localhost:8001/health
```

## 🔄 Updates

To update the system:

1. Backup your configuration
2. Pull latest changes
3. Update dependencies: `pip install -r requirements_local_mt5.txt`
4. Run tests: `python mt/test_mt5.py`
5. Update configuration if needed

---

**⚠️ DISCLAIMER**: This software is for educational purposes. Trading carries financial risk. Always test thoroughly before live trading.