# ZacQC Memory Leak Analysis Report

## Executive Summary
After analyzing the ZacQC codebase, I've identified several potential memory leaks that could cause RAM to continuously increase during backtesting. The main issues are related to data accumulation without proper cleanup, particularly in the RallyDetector and order tracking systems.

## Critical Memory Leaks Identified

### 1. **RallyDetector's data_cache - MAJOR LEAK**
**File:** `/ZacQC/management/rally_detector.py`
**Issue:** The `data_cache` list continuously accumulates price data for ALL symbols without cleanup
- **Line 50:** `self.data_cache.append(price_data)`
- **Problem:** The cache is limited to 960 entries (4 hours) PER SYMBOL, but it stores data for ALL symbols in a single list
- **Impact:** With 100 symbols, this could store 96,000 data points in memory

**Fix Required:**
```python
# Current problematic code:
self.data_cache.append(price_data)  # Stores all symbols in one list

# Should be:
# Store per-symbol data separately and clean up inactive symbols
if symbol not in self.data_cache:
    self.data_cache[symbol] = []
self.data_cache[symbol].append(price_data)
```

### 2. **Order Tracking Dictionaries - MODERATE LEAK**
**File:** `/ZacQC/trading/order_manager.py`
**Issue:** Order tracking dictionaries don't properly clean up completed orders
- `stop_loss_orders` (line 26)
- `profit_take_orders` (line 27)
- `entry_to_sltp_mapping` (line 30)

**Problem:** These dictionaries store order information but cleanup only happens on specific events, not when orders are completed/cancelled
**Impact:** Long-running backtests accumulate order history

### 3. **Symbol Managers Never Removed**
**File:** `/ZacQC/main.py`
**Issue:** `self.symbol_managers` dictionary (line 46) adds symbol managers but never removes them
- Symbol managers contain data managers, strategies, and other components
- Even if a symbol stops trading, its manager remains in memory

### 4. **DataManager Rolling Windows - MINOR ISSUE**
**File:** `/ZacQC/data/data_manager.py`
**Issue:** Rolling windows are oversized for their actual usage
- `bars_15s`: Set to 45 but only needs ~40
- `bars_daily`: Set to 35 but could be optimized
- `bars_1m` and `bars_weekly`: Allocated but barely used

### 5. **Strategy Condition States - MINOR LEAK**
**File:** `/ZacQC/core/strategy.py`
**Issue:** Duplicate condition state tracking
- Both legacy `condition_states` dict and new `c1-c5` variables
- `pending_orders` dictionary not always cleaned properly

### 6. **Daily Volume Tracking - MINOR LEAK**
**File:** `/ZacQC/data/data_manager.py`
**Issue:** `daily_volumes` list (line 41) accumulates volume data
- Limited to 7 days but created per symbol
- Not cleared when symbol becomes inactive

## Other Observations

### Not Memory Leaks (Properly Managed):
1. **Consolidators**: Properly managed by QuantConnect framework
2. **15-second bars cleanup**: Has daily cleanup routine (`_cleanup_old_15s_bars`)
3. **Order cancellation**: Has proper cleanup in `OnOrderEvent`
4. **Daily resets**: Most components have daily reset methods

### Performance Issues (Not Leaks):
1. **Excessive logging**: High-frequency logging in 15-second intervals
2. **Redundant calculations**: Some metrics recalculated unnecessarily

## Recommended Fixes

### Priority 1 - Fix RallyDetector data_cache
```python
# Change data_cache to per-symbol storage
def __init__(self, algorithm, params):
    self.data_cache = {}  # Changed from list to dict
    self.inactive_symbol_threshold = timedelta(hours=1)
    
def update_price_data(self, symbol, bar_data):
    if symbol not in self.data_cache:
        self.data_cache[symbol] = []
    
    # Add data
    self.data_cache[symbol].append(price_data)
    
    # Limit per-symbol cache
    if len(self.data_cache[symbol]) > max_entries:
        self.data_cache[symbol] = self.data_cache[symbol][-max_entries:]
    
    # Clean up inactive symbols periodically
    self._cleanup_inactive_symbols()

def _cleanup_inactive_symbols(self):
    current_time = self.algorithm.Time
    symbols_to_remove = []
    
    for symbol, data_list in self.data_cache.items():
        if data_list and (current_time - data_list[-1]['time']) > self.inactive_symbol_threshold:
            symbols_to_remove.append(symbol)
    
    for symbol in symbols_to_remove:
        del self.data_cache[symbol]
```

### Priority 2 - Clean Order Tracking
```python
# Add periodic cleanup for order tracking dictionaries
def cleanup_completed_orders(self):
    # Clean stop_loss_orders
    completed_sl = []
    for key, order_info in self.stop_loss_orders.items():
        order = order_info.get('order')
        if order and self._is_order_completed(order):
            completed_sl.append(key)
    
    for key in completed_sl:
        del self.stop_loss_orders[key]
    
    # Similar cleanup for profit_take_orders and entry_to_sltp_mapping
```

### Priority 3 - Symbol Manager Lifecycle
```python
# Add method to remove inactive symbol managers
def remove_inactive_symbol(self, symbol_name):
    if symbol_name in self.symbol_managers:
        # Cleanup symbol manager resources
        symbol_manager = self.symbol_managers[symbol_name]
        symbol_manager.cleanup()  # New method to clean resources
        del self.symbol_managers[symbol_name]
```

## Testing Recommendations

1. **Monitor memory usage** during backtests with many symbols
2. **Add memory profiling** to track object counts
3. **Implement periodic garbage collection** if needed
4. **Add debug logging** for cache sizes

## Conclusion

The primary memory leak is in the RallyDetector's data_cache, which accumulates data for all symbols without proper per-symbol management or cleanup. This, combined with the order tracking dictionaries and symbol manager retention, can cause significant memory growth during long backtests with many symbols.

Implementing the recommended fixes, particularly for the RallyDetector, should significantly reduce memory consumption during backtesting.