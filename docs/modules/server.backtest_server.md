# server.backtest_server
**Path:** `server/backtest_server.py`  
**Purpose:** Flask backend for orchestrating Lean backtests, configuration management, and data download toggles.  
**Public API:** `app`, `BacktestManager`, REST route handlers

## Quick Start
```python
from server.backtest_server import app

if __name__ == "__main__":
    app.run(port=8080)
```

## Public API
### Classes
- `BacktestManager()` — Coordinates data downloads, Lean CLI backtests, and log aggregation.  
  **Init params:** None.  
  **Key methods:** `start_backtest(...)`, `stop_backtest()`, `get_status()`, `get_logs(last_n)`.  
  **Raises:** Propagates subprocess errors when Lean commands fail.

### Functions
- `load_config_strict(config_path)` — Load ZacQC parameters into a dictionary.  
- `save_config_to_parameters_py(config_dict, config_path)` — Persist configuration changes.  
- `setup_logging()` — Configure rotating loggers.  
- `cleanup_old_backtests(backtests_dir, keep_latest, max_total_size_mb)` — Enforce retention policy.  
- `kill_process_on_port(port)` — Force free a TCP port prior to server start.

### Constants / Enums
- `CONFIG_FILE_PATH` — Absolute path to `ZacQC/config/parameters.py`.  
- `DISABLE_DATA_DOWNLOAD` — Global flag toggled via API to skip downloads.

## Design Notes
- **Dependencies:** Flask + CORS extensions, Lean CLI, Docker for container cleanup, and filesystem access to `ZacQC`.  
- **Invariants:** Logging directory structure must exist; Lean CLI commands execute relative to repo root.  
- **Performance considerations:** Background threads stream logs; retains last 1k entries to protect memory.

## Examples
```python
from server.backtest_server import BacktestManager

manager = BacktestManager()
manager.start_backtest("ZacQC")
status = manager.get_status()
```

## Known Limitations / TODOs
- Authentication and rate limiting are not implemented.  
- Data download batching currently fixed at one symbol per batch.

## See Also
- [Parent package](../modules/server.md)
- [Related module](../modules/server.trading_calendar.md)

Last updated: 2025-10-14
