# Running QuantConnect Lean Locally: Backtesting & Live Trading Guide

## Environment Setup (Unix-Based)

To run the QuantConnect **Lean Engine** locally, you need to set up your environment with Docker and the Lean CLI:

- **Install Docker**: Make sure Docker is installed and running on your system (Linux or macOS). Lean runs the engine inside Docker containers, which include a minimal OS, the Lean engine, and all required packages. (Refer to Docker’s official install guides for your OS.)

- **Install Lean CLI**: The Lean CLI is a Python-based tool distributed via pip. Install it using:  
  ```bash
  pip install --upgrade lean
  ```  
  This will install/upgrade the `lean` command-line tool. (Ensure you have Python and pip available.)

- **Authenticate with QuantConnect**: You need a QuantConnect account (with membership in an organization on a paid tier) to use the CLI fully. Log in by running:  
  ```bash
  lean login
  ```  
  You’ll be prompted for your **user ID** and **API token** (get these from your QuantConnect account page). The CLI will save them locally for API access.

- **Initialize a Lean Workspace**: Create a directory for your Lean projects and navigate into it. Then run:  
  ```bash
  lean init
  ```  
  This links the folder to your QuantConnect organization and scaffolds the required structure. The CLI will download a configuration file and sample data. After initialization, you should see:
  - **`lean.json`** – The Lean **configuration file** for local runs (with default settings).
  - **`data/`** – A data directory (with sub-folders like `equity`, `crypto`, etc., containing sample market data).
  - **`storage/`** – A folder for local object store (used by Lean for persistent storage).
  
  These are necessary for running backtests/live algorithms locally. Always run Lean CLI commands from this workspace root so it finds the `lean.json` config and data directories by default.

- **Create a Project**: Use the CLI to scaffold a new algorithm project. For example:  
  ```bash
  lean create-project "My First Project"
  ```  
  This creates a folder named **My First Project/** with a basic **`main.py`** (or `Main.cs` for C#) and a `research.ipynb` notebook to get started. It also includes editor config files (for VS Code, PyCharm, etc.) and a **`config.json`** inside the project, which holds project-specific settings. You can create multiple project folders for different strategies.

## Overview of the Lean Engine Framework

QuantConnect’s **Lean Engine** is an open-source, modular algorithmic trading engine for research, backtesting, and live trading. When running locally, the Lean engine operates inside a Docker container but uses the same codebase and architecture as on QuantConnect’s cloud. Key components of the Lean framework include:

- **Algorithm (QCAlgorithm)**: Your strategy code (Python or C#) which is executed by the engine. You define a subclass of `QCAlgorithm` with an `Initialize()` method and event handlers like `OnData(...)`. Lean loads this algorithm and manages its lifecycle.

- **Data Feed**: Feeds market data into your algorithm. In **backtesting**, the data feed reads historical data from disk (the `data/` directory) and sends it to the algorithm in time-sequence. In **live trading**, the data feed connects to live streams (from your broker or data provider) to supply real-time updates. Lean is data-agnostic – it supports equities, forex, crypto, etc., as long as data is available.

- **Scheduling & Time**: Lean’s engine advances time and triggers events. In backtests, time is simulated (fast-forward through historical dates). In live mode, the engine runs in real-time, aligning with actual clock and market hours. The **Real-time Handler** triggers scheduled events (e.g., End of Day events, or scheduled functions you set) in both modes (simulated timing for backtests, real clock for live).

- **Brokerage Integration**: In live trading, Lean connects to broker APIs through brokerage plugins (Interactive Brokers, Coinbase, OANDA, etc.). Orders placed by your algorithm are routed to the broker for execution. Lean includes brokerage adapters that translate your orders to API calls and handle confirmations. In backtesting, there is no external broker – orders are filled by Lean’s **transaction models** using simulated matching engines.

- **Transaction & Portfolio Management**: Lean’s **Transaction Handler** processes the orders your algorithm submits. In backtests it uses models (fill models, slippage, etc.) to simulate trades; in live mode it sends orders to the brokerage and tracks their status. The **Portfolio Manager** and **Security Manager** built into `QCAlgorithm` keep track of holdings, cash, and asset-specific calculations (profit, leverage, etc.) for you. This allows your algorithm to query portfolio state easily (e.g., `Portfolio["IBM"].Quantity`).

- **Result Handling**: All through a run, a **Result Handler** collects statistics, order fills, performance charts, and logging messages. In backtest mode, this culminates in a backtest result JSON file and console output. In live mode, results (like performance metrics) are continuously updated and logs are streamed. Lean can also send results to a GUI or web interface, but when running locally via CLI, results are saved to files and logs shown on the terminal.

- **Configuration (lean.json)**: The `lean.json` file governs engine behavior. It defines environments (backtesting vs live) and which components to use. For example, it includes settings like `live-mode` true/false, default brokerage, data provider, cash initial capital, etc. When you ran `lean init`, a default config was created based on QuantConnect’s latest Lean config file. You can edit this to tweak settings (for advanced use cases), but the defaults are sensible for starting out. In live trading, you may add your brokerage credentials or data-feed options here or supply them via CLI arguments.

**In summary**, the Lean engine orchestrates data → **Algorithm** → orders → **Brokerage/Simulation** → results in a loop. It abstracts away many low-level details (data file access, API calls, portfolio accounting) so you can focus on your strategy logic.

## Running Backtests Locally with Lean CLI

Local **backtesting** allows you to test your algorithm against historical data on your machine:

1. **Prepare Data**: Ensure you have the historical **data** required for your backtest in the `data/` directory. The Lean CLI provides a `lean data download` command to fetch data from QuantConnect’s Data Library (if you have a subscription). Alternatively, you can manually place data files in the appropriate subfolders (e.g., `data/equity/usa/minute/AAPL/` for minute data, etc.). Lean’s data directory structure must match the expected format (see QuantConnect docs for data format if adding your own). The sample data included during `lean init` is very limited, so you’ll likely need to download or add more for your symbols and dates.

2. **Run a Backtest**: Use the `lean backtest` command with your project name or path. For example:  
   ```bash
   lean backtest "My First Project"
   ```  
   This will build and run your algorithm in a Docker container using the **quantconnect/lean** engine image. The CLI looks for your algorithm file (e.g. `main.py` or `Main.cs`) in the project directory and executes the backtest. You’ll see live logs in the terminal as the backtest progresses (candles being processed, orders filled, etc.). The environment inside Docker mirrors QuantConnect’s cloud environment (same Lean version and packages), ensuring consistency between local and cloud results.

   - *Tip:* If your project is in a subfolder or has a space in its name, wrap the name in quotes as shown. You can also specify a path to the algorithm file instead of the project name.

3. **Backtest Output**: When the backtest finishes, Lean will output a **result JSON file** and related files in a timestamped folder under your project. For example: `My First Project/backtests/20231015_123456/` (the exact path is shown in the CLI output). This folder contains the complete results of the backtest, including `results.json` (performance metrics, trade statistics, charts) and maybe a `chart.png` if chart snapshots are saved. The console will usually summarize the results (e.g., total returns, runtime) and any errors. You can adjust the output directory with the `--output <path>` option when running the backtest (default is `PROJECT/backtests/<timestamp>` folder).

4. **Review Logs & Results**: Inspect the **`results.json`** for detailed metrics (you can programmatically parse it or use `lean report` to generate an HTML/PDF report). Check the console or log files for any error messages or warnings (for example, **missing data** warnings if your data folder lacked some history). Short log excerpts are in the JSON too. If you need to rerun with adjustments (say, different parameters or bug fixes), simply modify your code and run `lean backtest` again. Each run will create a new timestamped results folder.

**Example:** Running a backtest in the terminal might look like: 

```bash
$ lean backtest "My First Project"
# output (abbreviated):
# 20231015 13:30:00 Trace:: Engine.Run(): Lean initialized. Starting backtest...
# 20231015 13:30:00 Trace:: Algorithm.Initialize(): Portfolio set to $100000.00
# ...
# 20231015 13:30:05 Trace:: Backtest complete. Results saved to My First Project/backtests/20231015_133000/results.json
```

The above indicates a successful run with results stored for review.

## Running Live Trading Locally with Lean CLI

Lean can also be used for **live trading** on your local machine, connecting to brokerages through its integrations. Before starting, ensure you have the necessary API credentials and any required software from your brokerage (for example, IB **Interactive Brokers** requires IB Gateway or TWS – the Lean container will handle launching IB Gateway if configured, but you must have an IB account with API enabled).

**1. Configure Credentials & Environment:** Live trading requires specifying a **brokerage** and **data feed**. There are two ways to provide these:

- **Interactive Wizard (Prompt Mode):** Simply run `lean live "<ProjectName>"` without extra arguments. The CLI will interactively prompt you to select a brokerage from a list and then ask for all required credentials step-by-step. It will also ask to select a data feed (often you can use the broker as the data feed, or choose others like Polygon, etc.). This is convenient if you want to be guided through setup. The CLI saves your selections in the `lean.json` for next time where possible.

- **Non-Interactive (Command Flags):** If you prefer to script or repeat the same configuration, you can specify options on the command line. For example, to run live with Interactive Brokers as broker and data feed, you could use:  
  ```bash
  lean live "My First Project" --brokerage "Interactive Brokers" --data-feed "Interactive Brokers"       --ib-user-name <username> --ib-account <account> --ib-password <password>       --ib-enable-delayed-streaming-data true
  ```  
  This one-liner includes all needed flags (in this case enabling delayed data, as IB requires either market data subscriptions or allowing delayed data). You can also define an **environment** in `lean.json` (with `"live-mode": true` and all broker settings) and then just pass `--environment <name>` to use it. Using environment variables for secrets is a good practice: for instance, set `IB_USERNAME`, `IB_PASSWORD` in your shell profile and then run the command with `--ib-user-name $IB_USERNAME` etc., as shown in the example. This avoids exposing credentials in plaintext on the command line or config files.

**2. Start the Live Algorithm:** Execute the `lean live` command (with either interactive or preset options as above). For example:  
```bash
lean live "My First Project"
```  
Lean will launch a Docker container for the algorithm using the **quantconnect/lean** image (the live trading mode). If using Interactive Brokers, the container will attempt to start an **IB Gateway** session inside (you'll see logs about downloading brokerage modules and launching IB Gateway). If other brokerages (e.g., Coinbase, Oanda), it will connect via their APIs. In interactive mode, after entering credentials, Lean will begin streaming data and trading. In the console, you’ll start seeing log messages in real-time – for example, data subscription confirmations, order events, etc. The algorithm is now live and running continuously.

- Lean creates a **live results folder** similar to backtests: e.g., `My First Project/live/20231015_133000/` containing logs and any periodic result snapshots. Unlike a backtest, this isn’t a single summary at end (since live runs indefinitely); instead, it may update files over time. Key information like current holdings, profit, etc., can be found in these logs or through QuantConnect’s API if needed.

- **Console Logs**: The console will show info and error logs. You can keep this terminal open to monitor the strategy. If you started the live run in **detached mode** (`--detach` flag), the process runs in background (Docker container) and you can use `lean logs` to stream the logs or check the log file in the live folder.

**3. Managing the Live Session:** A live algorithm will keep running until you stop it (or it errors out). To **stop** a live trading session gracefully, you have two options:
  - If it’s running in the foreground, press **Ctrl+C** in that terminal. This will send a stop signal and terminate the Docker container.
  - Alternatively, run the CLI stop command from another terminal:  
    ```bash
    lean live stop "My First Project"
    ```  
    This will signal the running live container (identified by the project name) to shut down. The CLI will handle it cleanly, including disposing of brokerage connections.
  
  Make sure to stop the algorithm *before* attempting to restart it or before shutting down your machine. In case the CLI stop fails for any reason, you can manually stop the Docker container (e.g., `docker ps` to find it, then `docker stop <container-id>`), but that’s a last resort.

**Note:** When running live, be mindful of broker-specific requirements:
- Some brokers (like IB) require disabling two-factor auth or using specific settings for API access.
- Ensure you have the necessary data subscriptions (or use `--enable-delayed-streaming-data true` for IB paper trading to get delayed quotes without subscription).
- QuantConnect’s CLI may download plugin packages for the brokerage integrations on first use – let it finish those downloads. 

Once running, your strategy is live! You can monitor it via logs and also through your brokerage’s interface (positions and orders should reflect there). If you update your algorithm code and want to deploy changes, you’ll need to stop the current run and then restart `lean live` to pick up the new code. (If you are also using QuantConnect’s cloud, avoid running the same algorithm live in both places concurrently – one live instance per project).

## Interpreting Output Directories, Logs, and Results

When you run Lean locally, it produces organized output to help you analyze performance and debug issues:

- **Project Directory Structure**: Each project (algorithm) folder contains your code and a `config.json`. The `config.json` holds project-specific config like algorithm language, brokerage/environment overrides, etc., which the CLI or engine might use. You typically don’t need to edit this much (defaults are fine), but it’s good to know it’s there. The project folder is also where Lean stores results of backtests and live runs for that strategy.

- **Backtest Results**: Under the project folder, the CLI will create a `backtests/` subfolder. Each time you run `lean backtest`, a new folder is created with timestamp name. Inside, the primary file is usually `results.json` which contains the full backtest report data (trade-by-trade stats, equity curve, drawdown, etc.). You might also find `strategy equity.png` or similar chart images if generated. Use these outputs to evaluate your strategy’s historical performance. To view results in a more friendly format, you can run `lean report "<ProjectName>/backtests/<timestamp>/results.json"` which generates an HTML or PDF report with charts and statistics.

- **Live Results and Logs**: When you run `lean live`, the project gets a `live/` folder. Under it, each session (identified by start timestamp) will log information. Typically, you’ll see a `log.txt` (or similar) containing the live output logs. There may also be periodic snapshot JSON files or daily summaries that Lean writes. These are essentially the live analog to backtest results, but updated continuously. If your algorithm uses the Object Store or writes files, those might appear in the project `storage/` directory or elsewhere as configured.

- **Console vs File Logs**: Lean streams logs to the console by default. All those messages are also captured in the output directories. If you missed something in the scrollback, check the log file in the backtest/live folder. The logging includes `Debug`, `Error`, and `Trace` messages from your algorithm and the engine. **Errors** are important to investigate (e.g., runtime errors in your code, or exceptions from the engine). Warnings about missing data can indicate you need to download more data for a complete backtest. The `lean.json` setting `show-missing-data-logs` is true by default, so if a file was absent (say, a trading day’s file for a stock), you’ll see a message in logs.

- **Understanding JSON Results**: The backtest **results JSON** contains multiple sections: performance statistics (Sharpe, drawdown), a timeline of equity, lists of trades, and algorithm runtime statistics. It’s structured similarly to what you get from QuantConnect cloud backtests. You can open it in a text editor or use Python to parse it for custom analysis. Lean’s output does not automatically display charts on your local machine (unless you open the HTML report), so examining this JSON or the generated charts is how to visualize performance.

- **Lean Configuration (`lean.json`)**: This file in the workspace root is crucial for controlling runs. It includes settings like `environment` definitions. For example, an environment might specify which `IDataFeed` and `IBrokerage` implementations to use, and their configuration (API keys, etc.). When you ran interactive prompts for live, the CLI actually updated `lean.json` with a new environment entry for that brokerage (or it used the default live environment entry). You can manually edit `lean.json` to preset things if needed. For instance, you might create an `"InteractiveBrokers-Paper"` environment with your credentials so that you can run live without re-entering them. Keep in mind `lean.json` is a local file – protect it if it contains sensitive info (consider .gitignore if using version control).

- **Cleaning Up**: Over time, your backtests and live sessions may accumulate many timestamped folders. It’s up to you to clean these if disk space is a concern. You can delete old backtest result folders without issue. The `data/` folder can also grow large as you download more market history – organize or prune data as needed.

In short, **use the output files** to your advantage: after a backtest, review the results JSON for insights and ensure no errors in logs. During live runs, tail the log file or watch console output to verify the algorithm is functioning as expected (orders are being placed, etc.). All these artifacts ensure you have a full record of what Lean did during your runs.

## Best Practices for Managing Projects & Configurations

To efficiently run and manage Lean locally, consider the following best practices:

- **Use a Dedicated Workspace**: Keep all your projects under the organization workspace created by `lean init`. Run commands from this root so the CLI picks up the correct config and data paths. This avoids issues with missing config or relative path problems.

- **Keep Lean Updated**: The Lean CLI and Docker images are frequently updated with new features and fixes. Update them regularly:  
  - For CLI: `pip install --upgrade lean` (the CLI checks for updates daily and might warn you if out-of-date).  
  - For Docker images: run `lean update` or simply pull the latest `quantconnect/lean:latest` image. Up-to-date images ensure you have the latest brokerage integrations and bug fixes.

- **Version Control Your Code**: Treat each project like a software project. Use git or another VCS to track your algorithm code (`main.py`, etc.) and project config. QuantConnect’s cloud sync (`lean cloud push/pull`) can integrate with the CLI, but even for purely local projects, version control is wise. Exclude sensitive files like `lean.json` (if it contains API keys) or the large `data/` folder from your repository.

- **Manage Secrets Securely**: Avoid putting API keys or passwords directly in your algorithm code or in plain text config that could be shared. Use environment variables or the `lean.json` (which stays on your machine) for storing credentials. If using `lean.json`, consider the security of that file. The CLI also supports storing some credentials in a global config directory (like your QuantConnect API token was saved in `~/.lean/credentials`).

- **Testing before Live**: Always thoroughly backtest and, if possible, **paper trade** (many broker integrations allow paper trading mode) before running strategies with real money. Lean can run in paper mode by choosing “Paper Trading” as the brokerage (which doesn’t require real broker connection). This is a safe way to simulate live trading using real-time data without risking capital.

- **Monitoring Live Algorithms**: When your algorithm is live, monitor it closely at first. Watch the logs for errors or unexpected behavior. If you need to make code changes, **stop the live algorithm** (`lean live stop`) before redeploying. Running multiple instances of the same strategy on the same brokerage account can cause conflicts. It’s also good practice to have notifications in your algorithm (Lean’s `Notify` API) for critical events in live trading (e.g., email on error) – these will work if configured with your QuantConnect account’s notification settings.

- **Resource Management**: Docker will use your host’s resources. For intensive backtests, ensure your machine has enough memory/CPU allocated to Docker. On macOS, adjust Docker Desktop resources if needed. You can run multiple backtests in parallel by using the `--detach` option, but be mindful of resource contention. Similarly, for live, each live container will consume some resources continuously. Keep an eye on system load to avoid slowdowns or missed ticks.

- **Project Organization**: Give projects descriptive names and consider separating strategies into different projects rather than one giant project. Each project’s `config.json` can be used for strategy-specific parameters or references (for example, you might use it to store ticker lists or model parameters, which you can read in your code via the config).

- **Lean CLI Utilities**: Explore CLI commands like `lean research "<ProjectName>"` to open a Jupyter research notebook, or `lean optimize` for parameter optimization. While not needed for basic backtest/live, these can enhance your workflow. Also, `lean cloud pull/push` can sync with QuantConnect cloud – useful if you want to leverage cloud notebooks or share projects.

- **Troubleshooting**: If something isn’t working:
  - Run with `--verbose` to get debug logs from the CLI and engine for more detail.
  - Check that Docker is running and the container isn’t hitting permission issues (the workspace files are mounted into the container – ensure your user has rights, etc.).
  - If a live run isn’t starting, double-check all credentials and that your brokerage account is setup for API (e.g., for IB, ensure IB Gateway is not already running elsewhere and that your account isn’t logged in multiple times).
  - The QuantConnect community forums and documentation have specific guides for each brokerage if you run into integration-specific issues.

By following these practices, you’ll maintain a smooth local trading setup that mirrors professional development standards and avoids common pitfalls. Lean’s local platform gives you a lot of power and flexibility – with great power comes the need for careful management!

## Further Resources

- **QuantConnect Lean CLI Documentation** – Official documentation for all CLI commands and workflows.  
- **QuantConnect Lean Engine (GitHub)** – The open-source Lean Engine repository and wiki for in-depth technical reference.  
- **QuantConnect Forums & Tutorials** – Community-driven discussions and how-to guides for specific brokers and advanced usage (e.g., handling IB Gateway, custom data).  

Feel free to consult these resources for deeper exploration, but the guide above should enable you to efficiently run backtests and live algorithms on your local Unix-based system with QuantConnect Lean. Happy trading! 🚀


## IBKR (Brokerage) + Polygon (Live Data) Setup

This section shows how to run **Interactive Brokers (brokerage)** with **Polygon (live data provider)** locally using Lean CLI. It also covers multiple providers, history requests, and common flags.

### Quick start (non‑interactive)
Set credentials as environment variables, then deploy:

```bash
# IBKR
export IB_USERNAME="your-ib-username"
export IB_PASSWORD="your-ib-password"
export IB_ACCOUNT="DU1234567"   # or Uxxxxxxx for live

# Polygon
export POLYGON_API_KEY="your-polygon-key"

# Deploy live: IBKR brokerage + Polygon as the live data provider
lean live deploy "My Project"   --brokerage "Interactive Brokers"   --data-provider-live Polygon   --polygon-api-key "$POLYGON_API_KEY"   --ib-user-name "$IB_USERNAME"   --ib-account "$IB_ACCOUNT"   --ib-password "$IB_PASSWORD"   --ib-enable-delayed-streaming-data yes
```

**Notes**  
- `--ib-enable-delayed-streaming-data yes` lets Lean fall back to **delayed** IBKR quotes for assets you don’t have real‑time subscriptions for.  
- To also use Polygon for history/warm‑ups, add:  
  ```bash
  --data-provider-historical Polygon
  ```

### Interactive wizard (first run)
If you prefer prompts, run:
```bash
lean live deploy "My Project"
```
Then select **Interactive Brokers** for brokerage and **Polygon** for the live data provider when prompted, and provide your IBKR and Polygon credentials.

### Multiple data providers (order & fallback)
You can select more than one live provider. The **order matters**: Lean uses the **first** provider that supports a given security and falls back to the next for unsupported assets. A common setup is **Polygon first** (for US equities/options) and **IBKR second** (for futures or anything Polygon doesn’t cover).

### Platform caveat (IBKR local on Apple Silicon)
Per current docs, local live deployment with **IBKR on Apple Silicon (M1/M2/M3)** is not supported. If you’re on Apple Silicon, consider **cloud live** with IBKR, or run locally on x86_64.

### Troubleshooting & tips
- **Weekly re‑auth:** IBKR requires weekly re‑authentication via **IBKR Mobile (IB Key)**. The wizard will ask for a **Sunday UTC** restart time; keep your device available then.  
- **TWS/Gateway:** The CLI handles IB Gateway inside the container. Ensure your IB account supports API trading and that credentials are correct.  
- **Data coverage:** Polygon primarily covers **US equities/options**. For assets Polygon doesn’t provide (e.g., many futures), rely on IBKR as a secondary provider or choose another provider.

