# Empty if blocks with `if self.algorithm.enable_logging:` Pattern

## Summary
Found multiple instances where `if self.algorithm.enable_logging:` is followed by only commented lines and a `pass` statement. These could potentially cause IndentationError if the `pass` statement is removed or commented out.

## Locations Found:

### 1. `/home/cloudibkr/Documents/zac_qc/ZacQC/trading/conditions_checker.py`

**Lines 457-459:**
```python
if self.algorithm.enable_logging:
    # self.algorithm.Log(f"VWAP Condition Check LONG (HARD) - VWAP: {vwap_price:.4f}, Threshold: {hard_threshold:.4f}, Result: {result}")
    pass
```

**Lines 484-485:**
```python
if self.algorithm.enable_logging:
    pass  # self.algorithm.Log(f"VWAP Condition Check SHORT (HARD) - VWAP: {vwap_price:.4f}, Threshold: {hard_threshold:.4f}, Result: {result}")
```

### 2. `/home/cloudibkr/Documents/zac_qc/ZacQC/core/strategy.py`

**Lines 168-170:**
```python
if self.algorithm.enable_logging:
    # self.algorithm.Log(f"TRAILING UPDATE - {current_time}: {condition} OrderID={ticket.OrderId}, Entry Price={current_stop_price:.2f}, Market Price={current_price:.2f}, No Update Needed, Trailing %={trailing_pct:.3f}%")
    pass
```

### 3. `/home/cloudibkr/Documents/zac_qc/ZacQC/data/data_manager.py`

**Lines 117-119:**
```python
if self.algorithm.enable_logging:
    # self.algorithm.Log(f"15s Bar {self.symbol}: {bar.Time} | O:{bar.Open:.2f} H:{bar.High:.2f} L:{bar.Low:.2f} C:{bar.Close:.2f} V:{bar.Volume}")
    pass
```

## Potential Issues:
1. These blocks have logging statements that were commented out (likely for performance reasons)
2. The `pass` statement was added to prevent IndentationError
3. If someone removes or comments out the `pass` statement, it will cause an IndentationError

## Recommendations:
1. Consider removing the entire `if` block if logging is permanently disabled
2. Or use a configuration flag to control whether these specific verbose logs should be executed
3. Or keep the current structure but add a comment explaining why the `pass` is necessary

## Pattern to Search For:
To find all such occurrences in the future, use:
```bash
grep -r -A 3 "if self\.algorithm\.enable_logging:" . | grep -B 1 -A 2 "^\s*#\|pass"
```