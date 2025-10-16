# Referenced Expertise

## Scan @ 2025-10-16T07:53:51Z
- Keywords: polygon data, lean cli, data download, incremental sync
- Sources:
  - Experts/lean_unix_run.md
  - server/backtest_server.py
  - lean.json

### Notes
- Lean CLI’s `lean data download` command expects QuantConnect folder hierarchy and currently powers downloads; replacing it requires preserving on-disk layout.
- Existing backtest server batches Lean CLI downloads for daily/minute/second resolutions and relies on `_check_data_availability` to detect missing `data/equity/usa/second/<symbol>/<YYYYMMDD>_trade.zip` files using the US equity trading calendar.
- Polygon API credentials live under `polygon-api-key` in `lean.json`; the new downloader must read from there to authenticate.

### Context excerpts file
- Stored at `tasks/polygon-incremental-data-downloader-20251016T075149Z/references/excerpts/polygon-incremental-data-downloader-refs.txt`
