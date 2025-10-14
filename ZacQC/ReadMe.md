# Modular Trading Algorithm - QuantConnect Implementation

## Overview

This is a complete modular implementation of the trading algorithm originally built with ibinsync, now migrated to QuantConnect platform. The algorithm implements a sophisticated trading system with 5 distinct trading conditions, complete risk management, and comprehensive alerting.

## Architecture

The algorithm follows a modular design pattern with clear separation of concerns:

```
main.py (Main Algorithm)
├── parameters.py (Configuration)
├── data_manager.py (Data Processing)
├── metrics_calculator.py (Market Metrics)
├── conditions_checker.py (Trading Conditions)
├── order_manager.py (Order Execution)
├── trail_order_manager.py (Trail Orders)
├── risk_manager.py (Risk Management)
├── alert_manager.py (Notifications)
├── strategy.py (Account Strategies)
└── utils.py (Utility Functions)
```

## File Descriptions

### Core Files

- **`main.py`** - Main algorithm class, orchestrates all components
- **`parameters.py`** - All trading parameters and configuration (replaces Google Sheets)
- **`data_manager.py`** - Handles data consolidation, VWAP calculation, and bar management
- **`metrics_calculator.py`** - Calculates all 48+ trading metrics from original algorithm

### Trading Logic

- **`conditions_checker.py`** - Implements the 5 trading conditions with rally and VWAP validation
- **`order_manager.py`** - Handles order execution, fills, and position management
- **`trail_order_manager.py`** - Implements LimitTrail orders (replicates IB functionality)

### Management Systems

- **`risk_manager.py`** - Comprehensive risk management including P&L monitoring
- **`alert_manager.py`** - Alert system with rate limiting, email notifications
- **`strategy.py`** - Per-account strategy state management
- **`utils.py`** - Utility functions and helpers

## Key Features Implemented

### ✅ Complete Feature Set
- **5 Trading Conditions** - All original conditions with two-phase logic
- **LimitTrail Orders** - Full replication of Interactive Brokers trail orders
- **VWAP Analysis** - Real-time VWAP calculation and validation
- **Rally Conditions** - Complex rally pattern detection for all conditions
- **Risk Management** - Daily P&L limits, position sizing, risk thresholds
- **Time-Based Actions** - Breakeven moves and position closures
- **Comprehensive Metrics** - All 48+ metrics from original algorithm
- **Alert System** - Rate-limited notifications with email delivery
- **Multi-Account Support** - Per-account strategies and risk management

### ✅ Enhanced Features
- **Modular Design** - Clean separation of concerns
- **Configuration File** - Python-based parameters (no Google Sheets dependency)
- **Comprehensive Logging** - Detailed logging throughout all components
- **Error Handling** - Robust error handling and recovery
- **Status Monitoring** - Real-time status of all components

## Trading Conditions

### Condition 1: Long Entry (Downward Break + Rally)
- **Phase 1**: Price breaks below 30DMA range threshold
- **Phase 2**: VWAP validation + Rally pattern confirmation
- **Trail Logic**: Trails down using param4 and nominal range

### Condition 2: Long Entry (New Low + Rally)  
- **Phase 1**: New low break with range criteria
- **Phase 2**: VWAP validation + Rally pattern confirmation
- **Trail Logic**: Same as Condition 1

### Condition 3: Long Entry (Max Down vs 30DMA)
- **Direct Evaluation**: Maximum down percentage in 30 minutes vs 30DMA range
- **Trail Logic**: Trails down using param5 and current price

### Condition 4: Short Entry (Upward Break + Rally)
- **Phase 1**: Price breaks above 30DMA range threshold  
- **Phase 2**: VWAP validation + Rally pattern confirmation (inverted)
- **Trail Logic**: Trails up using param4 and nominal range

### Condition 5: Short Entry (New High + Rally)
- **Phase 1**: New high break with range criteria
- **Phase 2**: VWAP validation + Rally pattern confirmation (inverted)  
- **Trail Logic**: Same as Condition 4

## Configuration

### Basic Setup
```python
# In parameters.py, modify these key settings:

# Core parameters
self.param1 = 1.0  # Range break threshold
self.param2 = 2.0  # Range criteria threshold  
self.param3 = 3.0  # Max down threshold
self.param4 = 0.5  # Trail amount for cond1,2,4,5
self.param5 = 1.0  # Trail amount for cond3

# Profit targets
self.profittakeC1 = 2.0  # Condition 1 profit %
self.profittakeC2 = 2.5  # Condition 2 profit %
# ... etc

# Account configuration
self.accounts = [
    {'account_id': 'DU123456', 'cash_pct': 20.0}
]
```

### Risk Parameters
```python
# Risk management
self.max_daily_pnl = 5.0  # Maximum daily P&L %
self.maxCapitalPct = 50.0  # Maximum capital usage
self.stoploss = 2.0  # Stop loss percentage

# Thresholds
self.liquidity_threshold = 10.0  # Minimum liquidity (M$)
self.rangemultiple_threshold = 3.0  # Range multiplier limit
self.gap_threshold = 3.0  # Gap threshold
```

## Usage

### Running the Algorithm
1. Copy all files to your QuantConnect algorithm directory
2. Set `main.py` as your main algorithm file
3. Customize parameters in `parameters.py`
4. Deploy to QuantConnect

### Monitoring
The algorithm provides comprehensive logging:
```python
# Enable detailed logging in parameters.py
self.debug_mode = True
self.log_metrics = True
self.log_conditions = True
self.log_orders = True
```

### Alerts
Configure email alerts:
```python
# In parameters.py
self.email_alerts_enabled = True
self.alert_email = "your-email@example.com"
```

## Components Deep Dive

### Data Manager
- **15-second bars**: Primary trading timeframe
- **VWAP calculation**: Real-time volume-weighted average price
- **Data validation**: Late bar detection and quality checks
- **Historical data**: Daily, weekly, and minute bar management

### Metrics Calculator  
- **48+ metrics**: Complete replication of original algorithm metrics
- **Performance optimized**: Efficient calculation of complex metrics
- **Historical analysis**: Moving averages, ranges, gaps, volume analysis

### Risk Manager
- **P&L monitoring**: Real-time profit/loss tracking per account
- **Position limits**: Maximum capital and risk exposure controls
- **Market conditions**: Liquidity, volatility, and gap-based restrictions
- **Auto-liquidation**: Automatic position closure on limit breaches

### Trail Order Manager
- **IB-compatible**: Replicates Interactive Brokers LimitTrail orders
- **Dynamic trailing**: Price-based trail adjustments
- **Strategy integration**: Works with condition-specific trail prices

## Performance Considerations

### Optimizations
- **Cached calculations**: Expensive metrics are cached with expiry
- **Efficient data structures**: Rolling windows for time-series data
- **Minimal API calls**: Batched operations where possible
- **Memory management**: Automatic cleanup of old data

### Monitoring
- **Real-time status**: All components report their status
- **Performance metrics**: Calculation times and resource usage
- **Error tracking**: Comprehensive error logging and recovery

## Differences from Original

### Removed Dependencies
- ❌ Google Sheets integration (replaced with Python config)
- ❌ SQLite database (QuantConnect handles data persistence)
- ❌ External alert system (replaced with email alerts)
- ❌ Multi-symbol support (simplified to single symbol)

### Enhanced Features
- ✅ Better error handling and recovery
- ✅ Comprehensive logging and monitoring
- ✅ Modular, maintainable code structure
- ✅ Built-in parameter validation
- ✅ Real-time status reporting

## Customization

### Adding New Conditions
1. Add condition logic in `conditions_checker.py`
2. Add parameters in `parameters.py`
3. Update order execution in `order_manager.py`
4. Add alerts in `alert_manager.py`

### Modifying Risk Rules
1. Update validation logic in `risk_manager.py`
2. Add new parameters in `parameters.py`
3. Update alert thresholds in `alert_manager.py`

### Adding New Metrics
1. Add calculation in `metrics_calculator.py`
2. Use in conditions via `conditions_checker.py`
3. Add alerts if needed in `alert_manager.py`

## Troubleshooting

### Common Issues
1. **Orders not executing**: Check risk manager status and account settings
2. **Missing alerts**: Verify email configuration in parameters
3. **Condition not triggering**: Enable debug logging to trace condition logic
4. **Performance issues**: Check cache hit rates and data quality

### Debug Mode
Enable comprehensive debugging:
```python
# In parameters.py
self.debug_mode = True

# This enables detailed logging throughout all components
```

### Status Monitoring
Get real-time status:
```python
# In main algorithm, call:
risk_status = self.risk_manager.GetRiskStatus()
data_status = self.data_manager.GetDataQualityStatus()
alert_stats = self.alert_manager.GetAlertStatistics()
```

## Support

For issues or questions:
1. Check the comprehensive logging output
2. Review parameter configuration
3. Verify QuantConnect platform requirements
4. Enable debug mode for detailed tracing

---

**Note**: This implementation maintains the core trading logic and risk management of the original algorithm while providing a cleaner, more maintainable codebase suitable for the QuantConnect platform.