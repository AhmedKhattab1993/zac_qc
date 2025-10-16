# Playwright for Python: Guide to Testing Web Apps in Chromium

> This guide is written **to a coding agent**. Use it as a playbook to automate robust testing for web applications in **Chromium** using **Playwright for Python**. It covers unit/integration/E2E patterns, advanced features (parallelism, visual checks, network mocking, custom selectors, tracing), and best practices.

---

## Installation and Setup

**Prerequisites**
- Python 3.8+
- pip
- (Recommended) pytest

**Install Playwright and browsers**
```bash
pip install playwright
playwright install
# or only Chromium:
playwright install chromium
```

**Install the pytest plugin (recommended)**
```bash
pip install pytest-playwright
# then ensure browsers are installed
playwright install
```

**Project structure**
```
playwright-tests/
├── tests/
│   └── test_example.py
└── pytest.ini
```

**Pytest defaults (optional)**
```ini
# pytest.ini
[pytest]
addopts = --browser chromium --headed
```

---

## Test Levels: Unit, Integration, End‑to‑End

- **Unit tests**: pure Python; test functions/classes in isolation. Typically *no browser*. Use pytest/unittest.
- **Integration tests**: partial stack. Spin a local server and use Playwright to drive a page; mock external services to focus on your component/feature.
- **E2E tests**: full user workflows across the stack. Use Playwright to automate Chromium and assert visible outcomes.

**Organization tips**
- Keep tests in `tests/`. Use markers or subfolders: `tests/unit/`, `tests/integration/`, `tests/e2e/`.
- **Independence**: each test sets up its own state. Playwright provides a fresh **browser context** per test via pytest fixtures (cookies/storage isolated).
- **Page Object Model (POM)** to reduce duplication and centralize selectors.

**POM skeleton**
```python
# pages/login_page.py
class LoginPage:
    def __init__(self, page):
        self.page = page

    def load(self):
        self.page.goto("https://example.com/login")

    def login(self, user, pwd):
        self.page.fill("input[name='email']", user)
        self.page.fill("input[name='password']", pwd)
        self.page.get_by_role("button", name="Login").click()
```

```python
# tests/test_login.py
from playwright.sync_api import Page, expect
from pages.login_page import LoginPage

def test_valid_login(page: Page):
    login_page = LoginPage(page)
    login_page.load()
    login_page.login("user@example.com", "securePassword123")
    expect(page).to_have_url("**/dashboard")
    expect(page.get_by_text("Welcome, user!")).to_be_visible()
```

---

## Writing Tests with Playwright (Pytest + Sync API)

**Basic example**
```python
# tests/test_example.py
import re
from playwright.sync_api import Page, expect

def test_homepage_title_contains_playwright(page: Page):
    page.goto("https://playwright.dev/")
    expect(page).to_have_title(re.compile("Playwright"))

def test_get_started_link_navigates(page: Page):
    page.goto("https://playwright.dev/")
    page.get_by_role("link", name="Get started").click()
    expect(page.get_by_role("heading", name="Installation")).to_be_visible()
```

**Locators & assertions**
- Prefer **role**, **label**, **text**, or **data-testid**: `get_by_role`, `get_by_label`, `get_by_text`, `get_by_test_id`.
- Built-in **auto-waiting**: `expect(locator).to_be_visible()` waits up to timeout—avoid `time.sleep`.
- Use **stable** selectors; avoid brittle XPath or deeply coupled CSS chains.

**Sync vs Async**
- Pytest plugin fixtures (`page`, `context`, `browser`) are synchronous.
- If you prefer `asyncio`, use `playwright.async_api` + `pytest-asyncio` and manage Playwright startup/teardown in async fixtures yourself.

---

## Headless vs Headed

- **Headless** (default): faster, CI-friendly.
- **Headed**: debug/observe visually.

**CLI**
```bash
pytest --headed
pytest --headed --slowmo=50
```

**Manual**
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=50)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://example.com")
    # ...
```

Use headless for CI and bulk runs; switch to headed (and/or `slow_mo`) when debugging layout/timing issues.

---

## Parallel Execution & Isolation

**Parallel with xdist**
```bash
pip install pytest-xdist
pytest -n 4              # or: --numprocesses=auto
```

**Isolation strategy**
- One **context per test** (via `page`/`context` fixtures) -> isolated cookies/storage/session.
- Avoid sharing state across tests. If server-side state is mutated, create unique test data and clean up.
- Start expensive shared services (e.g., app server) via session-scoped fixtures, but keep per-test data isolated.

---

## Advanced Features

### 1) Visual Regression Testing

**Capture screenshots**
```python
page.goto("https://example.com")
page.screenshot(path="homepage.png")            # current viewport
page.screenshot(path="homepage_full.png", full_page=True)
```

**Typical workflow**
1. Generate **baseline** images for key pages/components.
2. On each run, capture current screenshots.
3. Compare to baseline with an image-diff (tolerance for antialiasing). Use Pillow/OpenCV or a pytest plugin.
4. Store diff artifacts (image overlays) for review. Keep environment consistent (OS/fonts/headless).

Use visual checks sparingly for critical UI; update baselines intentionally when UI changes.

### 2) Network Interception & Mocking

**Mock an API response**
```python
from playwright.sync_api import Page, expect

def test_fruit_api(page: Page):
    def handle_request(route, request):
        data = [{"id": 21, "name": "Strawberry"}]
        route.fulfill(json=data, status=200, headers={"content-type": "application/json"})

    page.route("**/api/v1/fruits", handle_request)
    page.goto("https://demo.playwright.dev/api-mocking")
    expect(page.get_by_text("Strawberry")).to_be_visible()
```

**Modify a real response**
```python
def augment_fruit_response(route, request):
    # Fetch real response once, then modify JSON
    original = route.fetch()
    data = original.json()
    data.append({"id": 100, "name": "Loquat"})
    route.fulfill(response=original, json=data)

page.route("**/api/v1/fruits", augment_fruit_response)
```

**Use cases**
- Force edge cases (timeouts, 404/500s, empty lists).
- Isolate frontend from flaky or rate-limited backends.
- Ensure deterministic, fast tests without third-party calls.

**Tips**
- Register routes **before** `goto()` or before the page triggers requests.
- Use `page.on("request"/"response")` to assert calls were made or log traffic.
- Consider HAR replay for fully offline flows when applicable.

### 3) Custom Selectors

Register a custom selector engine when built-ins aren’t enough (e.g., complex Shadow DOM or bespoke attributes).

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    p.selectors.register("tag", """
    {
      query(root, selector) { return root.querySelector(selector); },
      queryAll(root, selector) { return Array.from(root.querySelectorAll(selector)); }
    }
    """)
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://example.com")
    page.locator("tag=button").first.click()
```

Use **only** when needed—prefer built-in role/text/test-id selectors first.

### 4) Tracing & Debugging

**Record traces (Pytest)**
```bash
pytest --tracing=retain-on-failure
# or: --tracing=on
```

**Record traces (manual)**
```python
context = browser.new_context()
context.tracing.start(screenshots=True, snapshots=True, sources=True)
page = context.new_page()
# ... actions ...
context.tracing.stop(path="trace.zip")
```

Open traces with:
```bash
playwright show-trace trace.zip
# or open https://trace.playwright.dev and drop the file
```

**Interactive Inspector**
```bash
PWDEBUG=1 pytest -s -k test_name
# or insert:
# page.pause()
```
- Runs headed, pauses at test start (or pause point).
- Pick locators, step actions, inspect DOM/network/console.

**Extra artifacts**
- `--screenshot=only-on-failure | on`
- `--video=retain-on-failure | on`
- Console logs/network events via listeners for deeper diagnostics.

---

## Integration with Test Runners

### Pytest (recommended)

**Key fixtures**
- `browser`: underlying browser process.
- `context`: fresh browser context per test (isolated storage).
- `page`: a new page in that context.

**Useful CLI options**
```bash
pytest --browser chromium                # choose engine
pytest --browser chromium --headed       # show the browser
pytest --screenshot=only-on-failure      # capture final screenshot on failure
pytest --video=retain-on-failure         # video artifacts for failed tests
pytest --device="iPhone 13"              # device emulation
```

**Multi-browser (if needed)**
```bash
pytest --browser chromium --browser webkit
```

**Targeted runs**
```bash
pytest tests/test_login.py
pytest tests/test_login.py::test_valid_login
pytest -k "login and not slow"
```

### unittest or other frameworks

You can launch/teardown Playwright yourself:
```python
import unittest
from playwright.sync_api import sync_playwright

class UITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
    def tearDown(self):
        self.context.close()

    def test_title(self):
        self.page.goto("https://example.com")
        self.assertIn("Example", self.page.title())
```

For async workflows, use `playwright.async_api` with `pytest-asyncio` and write async fixtures to start/stop Playwright and create contexts/pages.

**CI notes**
- Use the official Playwright Docker images or run `playwright install` in the CI job.
- For Docker, run with `--ipc=host` to avoid Chromium shared memory issues.
- Persist trace/screenshot/video artifacts on failure for post-mortem.

---

## Best Practices & Common Pitfalls

**Do this**
- Test from the **user’s perspective** (visible outcomes, ARIA roles/text).
- Prefer **stable locators**: role/label/text/test-id over brittle XPath/CSS chains.
- Keep tests **focused** on a single behavior; split long flows into smaller cases.
- Ensure **independence**: no test order, no shared state. Use fixtures for setup/teardown.
- Leverage **auto-wait**: `expect(...).to_*` and locator waits, not `sleep`.
- Keep suites **fast**: parallelize, avoid unnecessary videos/screenshots, and reserve visual checks for critical UI.
- If cross-browser support matters, include **Firefox/WebKit** smoke runs routinely.
- Use fixtures for **expensive setup** (start server once), but keep per-test data clean.
- Capture **artifacts** (trace/screenshot/video) on CI failures for fast debugging.
- Use `PWDEBUG=1` and `page.pause()` for interactive debugging locally.

**Avoid this**
- Relying on fragile selectors (deep CSS/XPath), hidden elements, or internal implementation details.
- Inter-test dependencies or assuming execution order.
- Hard-coded sleeps; prefer condition-based waits.
- Skipping cleanup of created data/resources.
- Hitting third-party APIs in tests (mock them).

**Edge considerations**
- Handle dialogs/popups explicitly (`page.on("dialog", ...)`, `page.expect_popup()`).
- Control locale/timezone in contexts for consistent date/number rendering.
- Manage authentication efficiently (UI login per test for realism, or use API/session seeding when justified).

---

## Quick Reference (Chromium + Pytest)

**Run all tests (headless)**
```bash
pytest --browser chromium
```

**Debug a single test (headed + slowmo)**
```bash
pytest -k test_login --headed --slowmo=100
```

**Parallel**
```bash
pytest -n auto
```

**Artifacts on failure**
```bash
pytest --screenshot=only-on-failure --video=retain-on-failure --tracing=retain-on-failure
```

**Network mocking**
```python
page.route("**/api/*", lambda route, req: route.fulfill(json={"ok": True}))
```

**Visual**
```python
page.screenshot(path="baseline.png")
# compare against "baseline.png" with your image-diff tool
```

---

### Final Notes for the Coding Agent

- Default to **Chromium**, headless, parallel. Turn on headed/slowmo only when diagnosing.
- Build **POMs** for maintainability. Centralize locators.
- Make tests **deterministic** with network mocking and consistent environments.
- Always collect **debug artifacts** on CI failures (trace/screenshot/video).

Happy testing! 💻🧪
