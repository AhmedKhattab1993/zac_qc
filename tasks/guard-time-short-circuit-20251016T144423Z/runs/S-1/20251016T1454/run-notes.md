# Lean Backtest Attempt — 2025-10-16T14:54Z

- Command: `lean backtest ZacQC`
- Result: **Failed** — Lean engine aborted with `FileNotFoundException` for `Data/symbol-properties/symbol-properties-database.csv`.
- Next steps: Populate `/Lean/Data/symbol-properties/symbol-properties-database.csv` (via `lean data download` or syncing shared data folder) and re-run baseline vs post-change backtests to capture parity and runtime deltas.
