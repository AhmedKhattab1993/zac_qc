import { APIRequestContext, expect, test } from '@playwright/test';
import { ChildProcess, execFileSync, spawn } from 'child_process';
import fs from 'fs';
import os from 'os';
import path from 'path';

type StoryTag = 'S-1' | 'S-2';
type ScenarioName = 'missing-data' | 'cached-data';

interface ScenarioDetails {
  env: Record<string, string>;
  data_root: string;
  config_path: string;
  symbols: string[];
  start_date: string;
  end_date: string;
  trading_day: string;
}

interface StatusSnapshot {
  timestamp: string;
  status: string;
  phase: string | null;
  log_count: number;
}

interface ScenarioContext {
  story: StoryTag;
  scenario: ScenarioName;
  workspace: string;
  env: Record<string, string>;
  server: ChildProcess;
  runDir: string;
  logStream: fs.WriteStream;
  details: ScenarioDetails;
  statusHistory: StatusSnapshot[];
  startTime: number;
  runtimeSeconds?: number;
  logMarkers: {
    missingData: boolean;
    secondsAvailable: boolean;
    downloadComplete: boolean;
    leanStarted: boolean;
    backtestCompleted: boolean;
  };
}

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const FEATURE_DIR = path.resolve(
  REPO_ROOT,
  'tasks',
  'playwright-backtest-data-availability-20251016T100803Z',
);

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

let missingDataRuntime: number | undefined;

test.describe('Backtest data availability', () => {
  test('@missing-data [S-1] surfaces missing data path in UI', async ({ page, request }, testInfo) => {
    test.setTimeout(480_000);

    const ctx = await prepareScenario('S-1', 'missing-data', testInfo.title);

    try {
      await waitForServerReady(request);

      await page.goto('/');

      const startButton = page.locator('#start-btn');
      await expect(startButton).toBeEnabled();

      ctx.startTime = Date.now();
      await startButton.click();

      await waitForSpecificStatus(ctx, request, 'downloading_data', 45_000);
      await expect(page.locator('#status-text')).toContainText('Downloading Data');

      const missingDataEntry = await waitForLogSubstring(request, 'Missing data for', 60_000);
      ctx.logMarkers.missingData = Boolean(missingDataEntry);

      await waitForSpecificStatus(ctx, request, 'running_backtest', 120_000);
      const downloadEntry = await waitForLogSubstring(request, 'Phase completed', 120_000);
      ctx.logMarkers.downloadComplete = Boolean(downloadEntry);

      const finalStatus = await waitForSpecificStatus(ctx, request, 'completed', 300_000);
      ctx.runtimeSeconds = (Date.now() - ctx.startTime) / 1000;

      expect(ctx.runtimeSeconds).toBeLessThanOrEqual(300);

      const statusSet = new Set(ctx.statusHistory.map((entry) => entry.status));
      expect(statusSet.has('downloading_data')).toBeTruthy();
      expect(statusSet.has('running_backtest')).toBeTruthy();
      expect(finalStatus.status).toBe('completed');

      const leanStartedEntry = await waitForLogSubstring(request, 'Lean process started', 60_000);
      ctx.logMarkers.leanStarted = Boolean(leanStartedEntry);
      const backtestSuccessEntry = await waitForLogSubstring(request, 'Backtest completed successfully', 60_000);
      ctx.logMarkers.backtestCompleted = Boolean(backtestSuccessEntry);

      const logs = await fetchLogs(request);
      const messages = logs.logs.map((entry) => entry.message);

      ctx.logMarkers.downloadComplete = ctx.logMarkers.downloadComplete || messages.some((m) => m.includes('Phase completed'));
      ctx.logMarkers.leanStarted = ctx.logMarkers.leanStarted || messages.some((m) => /Lean process started/.test(m));
      ctx.logMarkers.backtestCompleted = ctx.logMarkers.backtestCompleted || messages.some((m) => /Backtest completed successfully/.test(m));

      expect(ctx.logMarkers.missingData || messages.some((m) => /Missing data for/.test(m))).toBeTruthy();
      expect(ctx.logMarkers.downloadComplete).toBeTruthy();
      expect(ctx.logMarkers.leanStarted).toBeTruthy();
      expect(ctx.logMarkers.backtestCompleted).toBeTruthy();

      missingDataRuntime = ctx.runtimeSeconds;
    } finally {
      await teardownScenario(ctx, request);
    }
  });

  test('@cached-data [S-2] skips redundant downloads when data exists', async ({ page, request }, testInfo) => {
    test.setTimeout(420_000);

    const ctx = await prepareScenario('S-2', 'cached-data', testInfo.title);

    try {
      await waitForServerReady(request);

      await page.goto('/');

      const startButton = page.locator('#start-btn');
      await expect(startButton).toBeEnabled();

      ctx.startTime = Date.now();
      await startButton.click();

      await waitForSpecificStatus(ctx, request, 'downloading_data', 45_000);
      const secondsAvailableEntry = await waitForLogSubstring(request, 'All required Seconds data is available', 60_000);
      ctx.logMarkers.secondsAvailable = Boolean(secondsAvailableEntry);

      await waitForSpecificStatus(ctx, request, 'running_backtest', 120_000);
      const downloadEntry = await waitForLogSubstring(request, 'Phase completed', 120_000);
      ctx.logMarkers.downloadComplete = Boolean(downloadEntry);

      const finalStatus = await waitForSpecificStatus(ctx, request, 'completed', 300_000);
      ctx.runtimeSeconds = (Date.now() - ctx.startTime) / 1000;

      expect(ctx.runtimeSeconds).toBeLessThanOrEqual(300);
      if (missingDataRuntime !== undefined) {
        expect(ctx.runtimeSeconds).toBeLessThanOrEqual(missingDataRuntime + 1); // allow small variance
      }

      const leanStartedEntry = await waitForLogSubstring(request, 'Lean process started', 60_000);
      ctx.logMarkers.leanStarted = Boolean(leanStartedEntry);
      const backtestSuccessEntry = await waitForLogSubstring(request, 'Backtest completed successfully', 60_000);
      ctx.logMarkers.backtestCompleted = Boolean(backtestSuccessEntry);

      const logs = await fetchLogs(request);
      const messages = logs.logs.map((entry) => entry.message);

      ctx.logMarkers.secondsAvailable = ctx.logMarkers.secondsAvailable || messages.some((m) => m.includes('All required Seconds data is available'));
      ctx.logMarkers.downloadComplete = ctx.logMarkers.downloadComplete || messages.some((m) => m.includes('Phase completed'));
      ctx.logMarkers.leanStarted = ctx.logMarkers.leanStarted || messages.some((m) => /Lean process started/.test(m));
      ctx.logMarkers.backtestCompleted = ctx.logMarkers.backtestCompleted || messages.some((m) => /Backtest completed successfully/.test(m));

      expect(ctx.logMarkers.secondsAvailable).toBeTruthy();
      expect(ctx.logMarkers.downloadComplete).toBeTruthy();
      expect(ctx.logMarkers.leanStarted).toBeTruthy();
      expect(ctx.logMarkers.backtestCompleted).toBeTruthy();

    } finally {
      await teardownScenario(ctx, request);
    }
  });
});

async function prepareScenario(story: StoryTag, scenario: ScenarioName, testTitle: string): Promise<ScenarioContext> {
  const workspace = await fs.promises.mkdtemp(path.join(os.tmpdir(), `zac-${scenario}-`));
  const cliOutput = execFileSync(
    'python',
    ['-m', 'tests.e2e.support.cli', scenario, '--workspace', workspace],
    {
      cwd: REPO_ROOT,
      env: { ...process.env, PYTHONUNBUFFERED: '1' },
    },
  );

  const details = JSON.parse(cliOutput.toString()) as ScenarioDetails;
  const { runDir } = createRunDirectory(story, scenario, testTitle);

  const logPath = path.join(runDir, 'server.log');
  const logStream = fs.createWriteStream(logPath, { flags: 'a' });

  const env = {
    ...process.env,
    ...details.env,
    PYTHONUNBUFFERED: '1',
    E2E_MODE: process.env.E2E_MODE ?? 'fast',
  };

  const server = spawn('python', ['start_server.py'], {
    cwd: REPO_ROOT,
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  server.stdout?.pipe(logStream, { end: false });
  server.stderr?.pipe(logStream, { end: false });

  return {
    story,
    scenario,
    workspace,
    env,
    server,
    runDir,
    logStream,
    details,
    statusHistory: [],
    startTime: Date.now(),
    logMarkers: {
      missingData: false,
      secondsAvailable: false,
      downloadComplete: false,
      leanStarted: false,
      backtestCompleted: false,
    },
  };
}

async function waitForServerReady(request: APIRequestContext, timeoutMs = 30_000): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await request.get('/api/backtest/status');
      if (response.ok()) {
        await response.dispose();
        return;
      }
      await response.dispose();
    } catch (error) {
      // server not ready yet
    }
    await sleep(500);
  }
  throw new Error('Timed out waiting for backtest server to become ready.');
}

async function waitForSpecificStatus(
  ctx: ScenarioContext,
  request: APIRequestContext,
  targetStatus: string,
  timeoutMs: number,
): Promise<any> {
  const deadline = Date.now() + timeoutMs;
  let lastBody: any = null;

  while (Date.now() < deadline) {
    const response = await request.get('/api/backtest/status');
    if (!response.ok()) {
      await response.dispose();
      await sleep(1000);
      continue;
    }

    const body = await response.json();
    await response.dispose();

    recordStatus(ctx, body);

    if (body.status === targetStatus) {
      return body;
    }

    lastBody = body;
    await sleep(1000);
  }

  throw new Error(
    `Timed out waiting for status '${targetStatus}'. Last response: ${JSON.stringify(lastBody)}`,
  );
}

async function waitForLogSubstring(
  request: APIRequestContext,
  substring: string,
  timeoutMs: number,
): Promise<{ timestamp: string; message: string }> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const logs = await fetchLogs(request);
    const lower = substring.toLowerCase();
    const match = logs.logs.find((entry) => entry.message.toLowerCase().includes(lower));
    if (match) {
      return match;
    }
    await sleep(1000);
  }
  throw new Error(`Log message containing '${substring}' not observed within timeout.`);
}

async function fetchLogs(request: APIRequestContext): Promise<{ logs: Array<{ timestamp: string; message: string }> }> {
  const response = await request.get('/api/backtest/logs', {
    params: { last_n: '500' },
  });
  if (!response.ok()) {
    const body = await response.text();
    await response.dispose();
    throw new Error(`Failed to fetch logs: ${body}`);
  }
  const data = await response.json();
  await response.dispose();
  return data;
}

async function teardownScenario(ctx: ScenarioContext, request: APIRequestContext): Promise<void> {
  try {
    const { logs } = await fetchLogs(request);
    await fs.promises.writeFile(
      path.join(ctx.runDir, 'logs.json'),
      JSON.stringify({ logs }, null, 2),
      'utf-8',
    );

    const leanLines = logs
      .filter((entry) => entry.message.includes('[BACKTEST EXECUTION]'))
      .map((entry) => `${entry.timestamp} ${entry.message}`)
      .join('\n');
    await fs.promises.writeFile(path.join(ctx.runDir, 'lean.log'), leanLines, 'utf-8');
  } catch (error) {
    // swallowing teardown errors keeps test failures focused on assertions
  }

  await fs.promises.writeFile(
    path.join(ctx.runDir, 'status-history.json'),
    JSON.stringify(ctx.statusHistory, null, 2),
    'utf-8',
  );

  const metricsPayload = {
    runtime_seconds: ctx.runtimeSeconds ?? null,
    status_history_entries: ctx.statusHistory.length,
    log_markers: ctx.logMarkers,
  };
  await fs.promises.writeFile(
    path.join(ctx.runDir, 'metrics.json'),
    JSON.stringify(metricsPayload, null, 2),
    'utf-8',
  );

  await fs.promises.writeFile(
    path.join(ctx.runDir, 'scenario.json'),
    JSON.stringify(ctx.details, null, 2),
    'utf-8',
  );

  await shutdownChild(ctx.server);
  ctx.logStream.end();
}

function recordStatus(ctx: ScenarioContext, body: any) {
  const snapshot: StatusSnapshot = {
    timestamp: new Date().toISOString(),
    status: body.status,
    phase: body.phase ?? null,
    log_count: body.log_count ?? 0,
  };

  const previous = ctx.statusHistory[ctx.statusHistory.length - 1];
  if (!previous || previous.status !== snapshot.status || previous.phase !== snapshot.phase) {
    ctx.statusHistory.push(snapshot);
  }
}

async function shutdownChild(child: ChildProcess, timeoutMs = 10_000): Promise<void> {
  if (child.killed) {
    return;
  }

  const exitPromise = new Promise<void>((resolve) => {
    child.once('exit', () => resolve());
    child.once('close', () => resolve());
  });

  child.kill('SIGTERM');

  const timeoutPromise = sleep(timeoutMs).then(() => {
    if (!child.killed) {
      child.kill('SIGKILL');
    }
  });

  await Promise.race([exitPromise, timeoutPromise]);
}

function createRunDirectory(story: StoryTag, scenario: ScenarioName, testTitle: string): { runDir: string } {
  const safeTitle = testTitle.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
  const runId = `${new Date().toISOString().replace(/[:.]/g, '-')}-${scenario}-${safeTitle}`;
  const runDir = path.join(FEATURE_DIR, 'runs', story, runId);
  fs.mkdirSync(runDir, { recursive: true });
  return { runDir };
}
