import { defineConfig, devices } from '@playwright/test';
import path from 'path';

const REPO_ROOT = __dirname;
const FEATURE_DIR = path.resolve(
  REPO_ROOT,
  'tasks',
  'playwright-backtest-data-availability-20251016T100803Z',
);

export default defineConfig({
  testDir: path.resolve(REPO_ROOT, 'tests', 'e2e'),
  timeout: 120_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: 'http://localhost:8080',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 15_000,
  },
  outputDir: path.join(FEATURE_DIR, 'artifacts', 'playwright-output'),
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
