# Decision Log

## [S-1] Missing data Playwright spec
- **Timestamp:** 2025-10-16T11:08:00-04:00
- **Action:** Implemented env overrides, fixtures, and `@missing-data` Playwright flow. Recorded runtime and artifacts.
- **Commands:**
  - `pytest -q tests/e2e/support/test_backtest_harness.py`
  - `E2E_MODE=fast npx playwright test tests/e2e/backtest-data-availability.spec.ts -g "@missing-data" --project=chromium --workers=1 --retries=0`
- **Evidence:** `tasks/playwright-backtest-data-availability-20251016T100803Z/runs/S-1/2025-10-16T11-07-56-417Z-missing-data-missing-data-s-1-surfaces-missing-data-path-in-ui/`
- **Runtime:** ~138s to completion (data download + Lean). Above 90s target but under 3 min; flagged for follow-up.

## [S-2] Cached data Playwright spec
- **Timestamp:** 2025-10-16T11:12:45-04:00
- **Action:** Seeded cached seconds data fixture and executed `@cached-data` Playwright flow confirming cached path.
- **Commands:**
  - `E2E_MODE=fast npx playwright test tests/e2e/backtest-data-availability.spec.ts -g "@cached-data" --project=chromium --workers=1 --retries=0`
  - `E2E_MODE=fast npx playwright test tests/e2e/backtest-data-availability.spec.ts --project=chromium --workers=1 --retries=0`
- **Evidence:** `tasks/playwright-backtest-data-availability-20251016T100803Z/runs/S-2/2025-10-16T11-12-01-894Z-cached-data-cached-data-s-2-skips-redundant-downloads-when-data-exists/`
- **Runtime:** ~126s (seconds data pre-seeded). Within 3 min budget and faster than missing-data path.
