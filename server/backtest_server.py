#!/usr/bin/env python3
"""
Backtest Control Server
Flask backend for starting/stopping QuantConnect backtests with Configuration Editor
"""

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import subprocess
import os
import threading
import json
import sys
import signal
import socket
import logging
import logging.handlers
import shutil
from datetime import datetime
from .trading_calendar import USEquityTradingCalendar

# Add parent directory to path for config imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# ZacQC uses parameters.py instead of complete_strategy_config.py
# from ZacQC.complete_strategy_config import load_config_strict, CompleteIBStrategyConfig

# Functions for ZacQC parameters.py handling
def load_config_strict(config_path):
    """Load ZacQC configuration from parameters.py"""
    import sys
    import importlib.util
    import os
    
    try:
        # Add the directory to Python path
        config_dir = os.path.dirname(config_path)
        if config_dir not in sys.path:
            sys.path.insert(0, config_dir)
        
        # Load the module
        spec = importlib.util.spec_from_file_location("parameters", config_path)
        parameters_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(parameters_module)
        
        # Create instance and properly initialize with CURRENT values from parameters.py
        params = parameters_module.TradingParameters()
        
        # Convert to dictionary for API compatibility
        config_dict = {}
        for attr_name in dir(params):
            if not attr_name.startswith('_') and not callable(getattr(params, attr_name)):
                value = getattr(params, attr_name)
                # Handle time objects
                if hasattr(value, 'strftime'):
                    # Format time without leading zeros for hours
                    hour = value.hour
                    minute = value.minute
                    config_dict[attr_name] = f"{hour}:{minute:02d}"
                else:
                    config_dict[attr_name] = value
        
        return config_dict
    except Exception as e:
        logging.error(f"Failed to load parameters.py: {e}")
        return {}

def save_config_to_parameters_py(config_dict, config_path):
    """Save configuration back to parameters.py file"""
    import re
    from datetime import time
    
    try:
        # Read the current file
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Update each parameter in the file
        for key, value in config_dict.items():
            if key == 'accounts':  # Skip accounts only
                continue
                
            # Handle different types
            if key == 'symbols' and isinstance(value, list):
                # Handle symbols list specially
                # Convert list to proper Python syntax with proper formatting
                if len(value) == 0:
                    value_str = "[]"
                else:
                    # Format as multi-line list
                    symbols_formatted = ",\n            ".join([f"'{sym}'" for sym in value])
                    value_str = f"[\n            {symbols_formatted}\n        ]"
            elif isinstance(value, bool):
                value_str = str(value)
                logger.info(f"DEBUG save_config_to_parameters_py: {key} = {value} -> {value_str}")
            elif isinstance(value, str) and ':' in value and (len(value) == 4 or len(value) == 5):  # Time format H:MM or HH:MM
                hour, minute = value.split(":")
                # Strip leading zeros and convert to int to avoid octal literal issues
                hour = int(hour)
                minute = int(minute)
                value_str = f'time({hour}, {minute})'
            elif isinstance(value, str):
                value_str = f'"{value}"'
            else:
                value_str = str(value)
            
            # Find and replace the parameter line, preserving comments
            if key == 'symbols':
                # Special handling for symbols - match multi-line list
                pattern = rf'(\s*self\.symbols\s*=\s*)\[[^\]]*\]'
                content = re.sub(pattern, rf'\1{value_str}', content, flags=re.DOTALL)
            else:
                pattern = rf'(\s*self\.{re.escape(key)}\s*=\s*)([^#\n]+)(#.*)?'
                
                def replace_func(match):
                    prefix = match.group(1)
                    comment = match.group(3) if match.group(3) else ""
                    if comment:
                        return f"{prefix}{value_str} {comment}"
                    else:
                        return f"{prefix}{value_str}"
                
                content = re.sub(pattern, replace_func, content)
        
        # Write back to file
        with open(config_path, 'w') as f:
            f.write(content)
        
        return True
    except Exception as e:
        logging.error(f"Failed to save to parameters.py: {e}")
        return False

# Setup comprehensive logging
def setup_logging():
    """Setup comprehensive logging for server operations"""
    
    # Create logs directory
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-20s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Root logger setup
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 1. Main server log file (rotating)
    server_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "backtest_server.log"),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    server_handler.setLevel(logging.DEBUG)
    server_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(server_handler)
    
    # 2. Request processing log (separate file)
    request_logger = logging.getLogger('request_processor')
    request_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "request_processing.log"),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    request_handler.setLevel(logging.INFO)
    request_handler.setFormatter(detailed_formatter)
    request_logger.addHandler(request_handler)
    request_logger.setLevel(logging.INFO)
    request_logger.propagate = False  # Don't duplicate in main log
    
    # 3. Backtest execution log (separate file)
    backtest_logger = logging.getLogger('backtest_executor')
    backtest_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "backtest_execution.log"),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    backtest_handler.setLevel(logging.DEBUG)
    backtest_handler.setFormatter(detailed_formatter)
    backtest_logger.addHandler(backtest_handler)
    backtest_logger.setLevel(logging.DEBUG)
    backtest_logger.propagate = False
    
    # 4. Console output (optional, for development)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # 5. Flask request logger
    flask_logger = logging.getLogger('werkzeug')
    flask_handler = logging.FileHandler(os.path.join(log_dir, "flask_requests.log"))
    flask_handler.setFormatter(detailed_formatter)
    flask_logger.addHandler(flask_handler)
    
    return log_dir

# Initialize logging
LOG_DIR = setup_logging()
logger = logging.getLogger(__name__)
request_logger = logging.getLogger('request_processor')
backtest_logger = logging.getLogger('backtest_executor')

def cleanup_old_backtests(backtests_dir, keep_latest=5, max_total_size_mb=500):
    """Clean up old backtest results to prevent disk space issues
    
    Args:
        backtests_dir: Path to the backtests directory
        keep_latest: Number of latest backtests to keep (default: 5)
        max_total_size_mb: Maximum total size in MB for all backtests (default: 500MB)
    """
    try:
        if not os.path.exists(backtests_dir):
            return
            
        # Get all backtest directories (format: YYYY-MM-DD_HH-MM-SS)
        backtest_dirs = []
        for item in os.listdir(backtests_dir):
            item_path = os.path.join(backtests_dir, item)
            if os.path.isdir(item_path) and item.count('-') == 4 and item.count('_') == 1:
                try:
                    # Parse directory name to get timestamp
                    dir_time = datetime.strptime(item, "%Y-%m-%d_%H-%M-%S")
                    # Get directory size
                    dir_size = sum(os.path.getsize(os.path.join(dirpath, filename))
                                 for dirpath, dirnames, filenames in os.walk(item_path)
                                 for filename in filenames)
                    backtest_dirs.append((item_path, dir_time, dir_size))
                except:
                    continue
        
        # Sort by timestamp (newest first)
        backtest_dirs.sort(key=lambda x: x[1], reverse=True)
        
        # Remove old backtests if we have more than keep_latest
        if len(backtest_dirs) > keep_latest:
            for path, _, _ in backtest_dirs[keep_latest:]:
                logger.info(f"🗑️ Removing old backtest: {os.path.basename(path)}")
                shutil.rmtree(path)
            backtest_dirs = backtest_dirs[:keep_latest]
        
        # Check total size and remove oldest if exceeds limit
        total_size_mb = sum(size for _, _, size in backtest_dirs) / (1024 * 1024)
        while total_size_mb > max_total_size_mb and len(backtest_dirs) > 1:
            oldest = backtest_dirs.pop()
            logger.info(f"🗑️ Removing backtest due to size limit: {os.path.basename(oldest[0])}")
            shutil.rmtree(oldest[0])
            total_size_mb = sum(size for _, _, size in backtest_dirs) / (1024 * 1024)
            
        logger.info(f"📊 Backtest cleanup complete. Kept {len(backtest_dirs)} backtests, total size: {total_size_mb:.1f}MB")
        
    except Exception as e:
        logger.error(f"❌ Error during backtest cleanup: {e}")

def kill_process_on_port(port):
    """Kill any process using the specified port"""
    try:
        # Check if port is in use
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(('localhost', port))
            if result != 0:
                print(f"✅ Port {port} is available")
                return
        
        print(f"🔍 Port {port} is in use, finding and killing the process...")
        
        # Find process using the port (works on macOS/Linux)
        result = subprocess.run(['lsof', '-ti', f':{port}'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    print(f"🔪 Killing process {pid} on port {port}")
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        # Give it a moment to terminate gracefully
                        import time
                        time.sleep(1.5)
                        
                        # Check if process is still running
                        try:
                            os.kill(int(pid), 0)  # Check if process exists
                            # If we get here, process is still running, force kill
                            print(f"⚡ Force killing process {pid}")
                            os.kill(int(pid), signal.SIGKILL)
                            time.sleep(0.5)
                        except ProcessLookupError:
                            pass  # Process already terminated
                            
                    except (ProcessLookupError, ValueError):
                        pass  # Process already terminated or invalid PID
            
            print(f"✅ Cleaned up port {port}")
            
            # Give the system a moment to free up the port
            import time
            time.sleep(1)
        else:
            print(f"⚠️ Could not find process using port {port}")
            
    except Exception as e:
        print(f"❌ Error cleaning up port {port}: {e}")

app = Flask(__name__)
# Configure CORS - uncomment and modify the line below for production with specific origins
# CORS(app, origins=['http://your-domain.com', 'https://your-domain.com'])
CORS(app)  # Allow all origins - change for production

# Request logging middleware
@app.before_request
def log_request_info():
    """Log detailed request information"""
    request_logger.info(f"REQUEST START: {request.method} {request.url}")
    request_logger.info(f"Headers: {dict(request.headers)}")
    request_logger.info(f"Remote addr: {request.remote_addr}")
    request_logger.info(f"User agent: {request.headers.get('User-Agent', 'Unknown')}")
    
    if request.is_json and request.get_json():
        request_logger.info(f"JSON payload: {request.get_json()}")
    elif request.form:
        request_logger.info(f"Form data: {dict(request.form)}")
    elif request.args:
        request_logger.info(f"Query params: {dict(request.args)}")

@app.after_request
def log_response_info(response):
    """Log response information"""
    request_logger.info(f"RESPONSE: {response.status_code} - {response.status}")
    request_logger.info(f"Response headers: {dict(response.headers)}")
    
    # Log response size
    if hasattr(response, 'content_length') and response.content_length:
        request_logger.info(f"Response size: {response.content_length} bytes")
    
    return response

# Global state
backtest_process = None
backtest_status = "idle"  # idle, running, completed, error
backtest_logs = []
backtest_results = None
latest_results_path = None

# Global flag to disable all data downloads
DISABLE_DATA_DOWNLOAD = False  # Set to True to skip all data downloads and use only local data

# Config file path - use ZacQC/config/parameters.py directly as requested
CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ZacQC", "config", "parameters.py")

class BacktestManager:
    def __init__(self):
        self.process = None
        self.download_process = None  # Track download process for cancellation
        self.status = "idle"  # idle, downloading_data, running_backtest, completed, error, cancelled
        self.phase = None  # data_download, backtest_execution
        self.logs = []
        self.start_time = None
        self.end_time = None
        self.data_download_time = None
        self.backtest_start_time = None
        # Track download details for status display
        self.download_symbols = []
        self.download_date_range = {}
        self.download_progress = {}
    
    def _check_data_availability(self, symbols, start_date, end_date, polygon_api_key):
        """Check if second-level trading data is available for all symbols and trading days"""
        import os
        
        check_start_time = datetime.now()
        backtest_logger.info(f"🔍 DATA CHECK: Verifying data availability for {len(symbols)} symbols from {start_date} to {end_date}")
        
        # Parse date strings
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        missing_symbols = []  # List of symbols that need downloading
        available_symbols = []  # List of symbols with complete data
        
        # Get base data directory
        base_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "equity", "usa", "second")
        
        for symbol in symbols:
            symbol_lower = symbol.lower()
            symbol_dir = os.path.join(base_data_dir, symbol_lower)
            
            self.logs.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "message": f"🔍 [DATA CHECK] Checking data for {symbol}...",
                "phase": "data_download"
            })
            
            if not os.path.exists(symbol_dir):
                missing_symbols.append(symbol)
                backtest_logger.warning(f"🔍 DATA CHECK: Missing directory for {symbol} - needs download")
                continue
            
            # Initialize trading calendar for accurate trading day validation
            trading_calendar = USEquityTradingCalendar(polygon_api_key)
            
            # Get actual trading days (excludes weekends AND market holidays)
            trading_days = trading_calendar.get_trading_days(start_dt.date(), end_dt.date())
            
            symbol_missing_days = []
            symbol_available_days = []
            
            # Check each actual trading day
            for trading_day in trading_days:
                date_str = trading_day.strftime('%Y%m%d')
                trade_file = f"{date_str}_trade.zip"
                trade_path = os.path.join(symbol_dir, trade_file)
                
                if os.path.exists(trade_path):
                    symbol_available_days.append(date_str)
                else:
                    symbol_missing_days.append(date_str)
            
            if symbol_missing_days:
                missing_symbols.append(symbol)
                backtest_logger.warning(f"🔍 DATA CHECK: {symbol} missing {len(symbol_missing_days)} days: {symbol_missing_days[:5]}{'...' if len(symbol_missing_days) > 5 else ''}")
            else:
                available_symbols.append(symbol)
                backtest_logger.info(f"🔍 DATA CHECK: {symbol} has complete data ({len(symbol_available_days)} trading days)")
        
        # Log summary with timing
        check_end_time = datetime.now()
        check_duration = (check_end_time - check_start_time).total_seconds()
        
        if missing_symbols:
            self.logs.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "message": f"⚠️ [DATA CHECK] Check completed in {check_duration:.1f}s - Missing data for {len(missing_symbols)} symbols: {', '.join(missing_symbols)}",
                "phase": "data_download"
            })
            self.logs.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "message": f"✅ [DATA CHECK] Complete data for {len(available_symbols)} symbols: {', '.join(available_symbols) if available_symbols else 'None'}",
                "phase": "data_download"
            })
            backtest_logger.info(f"🔍 DATA CHECK: Completed in {check_duration:.1f}s - {len(missing_symbols)} missing, {len(available_symbols)} available")
            return False, missing_symbols
        else:
            self.logs.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "message": f"✅ [DATA CHECK] Check completed in {check_duration:.1f}s - All data available for {len(symbols)} symbols: {', '.join(symbols)}",
                "phase": "data_download"
            })
            backtest_logger.info(f"🔍 DATA CHECK: Completed in {check_duration:.1f}s - All {len(symbols)} symbols have complete data")
            return True, available_symbols
    
    def _start_lean_execution(self, algorithm_name, config_params):
        """Start the Lean backtest execution"""
        # Build command to use local data
        cmd = ["lean", "backtest", algorithm_name, "--no-update"]
        
        # Do NOT add Polygon data provider - use local downloaded data instead
        # The lean backtest will automatically use the data downloaded above
        
        self.logs.append({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "message": "🏠 [BACKTEST EXECUTION] Using local data (no live API calls during backtest)",
            "phase": "backtest_execution"
        })
        backtest_logger.info("🏠 BACKTEST EXECUTION: Configured to use local data")
        
        self.logs.append({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "message": f"✅ [BACKTEST EXECUTION] Config file ready: {CONFIG_FILE_PATH}",
            "phase": "backtest_execution"
        })
        backtest_logger.info(f"✅ BACKTEST EXECUTION: Config file ready at {CONFIG_FILE_PATH}")
        
        # Algorithm parameters are passed via the configuration file in data folder
        # No need to pass individual parameters to Lean CLI as they're loaded from the config file
        self.logs.append({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "message": f"✅ [BACKTEST EXECUTION] Config file prepared in data folder for algorithm access",
            "phase": "backtest_execution"
        })
        backtest_logger.info(f"✅ BACKTEST EXECUTION: Config file ready at {CONFIG_FILE_PATH}")
        
        # Add additional config parameters if provided
        if config_params:
            for key, value in config_params.items():
                cmd.extend([f"--{key}", str(value)])
        
        try:
            self.logs.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "message": f"⚡ [BACKTEST EXECUTION] Launching Lean CLI with command: {' '.join(cmd)}",
                "phase": "backtest_execution"
            })
            backtest_logger.info(f"⚡ BACKTEST EXECUTION: Launching command: {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            
            # Start log monitoring thread
            threading.Thread(target=self._monitor_logs, daemon=True).start()
            
            self.logs.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "message": f"✅ [BACKTEST EXECUTION] Lean process started (PID: {self.process.pid})",
                "phase": "backtest_execution"
            })
            backtest_logger.info(f"✅ BACKTEST EXECUTION: Process started with PID {self.process.pid}")
            
        except Exception as e:
            self.status = "error"
            backtest_logger.error(f"❌ BACKTEST EXECUTION: Failed to start Lean process: {e}")
            raise
        
    def start_backtest(self, algorithm_name="ZacQC", config_params=None):
        """Start a new backtest (returns immediately, runs in background)"""
        backtest_logger.info(f"🚀 Starting backtest for algorithm: {algorithm_name}")
        
        # Clean up old backtest results before starting new one
        backtests_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                    algorithm_name, "backtests")
        cleanup_old_backtests(backtests_dir, keep_latest=5, max_total_size_mb=250)
        
        if self.process and self.process.poll() is None:
            backtest_logger.warning("❌ Backtest already running, rejecting new request")
            return {"error": "Backtest already running"}
        
        if self.status in ["downloading_data", "running_backtest"]:
            backtest_logger.warning("❌ Backtest already in progress, rejecting new request")
            return {"error": "Backtest already in progress"}
        
        # Start the backtest in a background thread
        import threading
        thread = threading.Thread(target=self._run_backtest_async, args=(algorithm_name, config_params))
        thread.daemon = True
        thread.start()
        
        backtest_logger.info(f"🚀 Backtest thread started for algorithm: {algorithm_name}")
        return {"message": "Backtest started successfully", "status": "starting"}
    
    def _run_backtest_async(self, algorithm_name="ZacQC", config_params=None):
        """Run the actual backtest logic in background thread"""
        try:
            self._execute_backtest_sync(algorithm_name, config_params)
        except Exception as e:
            backtest_logger.error(f"❌ Backtest execution failed: {e}")
            self.status = "error"
            self.end_time = datetime.now()
            self.logs.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "message": f"❌ [ERROR] Backtest failed: {str(e)}",
                "phase": "error"
            })
    
    def _execute_backtest_sync(self, algorithm_name="ZacQC", config_params=None):
        """Execute the actual backtest logic (synchronous)"""
        
        # Initialize phase tracking
        self.status = "downloading_data"
        self.phase = "data_download"
        self.logs = []
        self.start_time = datetime.now()
        self.end_time = None
        self.data_download_time = None
        self.backtest_start_time = None
        # Reset download tracking
        self.download_symbols = []
        self.download_date_range = {}
        self.download_progress = {}
        
        backtest_logger.info(f"🏁 PHASE 1: DATA DOWNLOAD - Starting data preparation at {self.start_time}")
        
        # Load config to get symbols and date range for data download - NO DEFAULTS
        try:
            # Ensure config directory exists
            config_dir = os.path.dirname(CONFIG_FILE_PATH)
            os.makedirs(config_dir, exist_ok=True)
            
            # Load configuration from parameters.py
            config = load_config_strict(CONFIG_FILE_PATH)
            
            # Require these values to be present in config - no defaults
            if 'symbols' not in config:
                raise ValueError("Config must contain 'symbols' field")
            if 'start_date' not in config:
                raise ValueError("Config must contain 'start_date' field")
            if 'end_date' not in config:
                raise ValueError("Config must contain 'end_date' field")
                
            symbols = config['symbols']
            start_date = config['start_date']
            end_date = config['end_date']
            should_download = True
            
            # Store download details for status display
            self.download_symbols = symbols
            self.download_date_range = {
                "start": start_date,
                "end": end_date
            }
            
            self.logs.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "message": f"🗂️ [DATA DOWNLOAD] Preparing data download for symbols: {', '.join(symbols)}",
                "phase": "data_download"
            })
            self.logs.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "message": f"📅 [DATA DOWNLOAD] Date range: {start_date} to {end_date}",
                "phase": "data_download"
            })
            symbols_str = ', '.join(symbols) if isinstance(symbols, list) else str(symbols)
            backtest_logger.info(f"📊 DATA DOWNLOAD: Symbols={symbols_str}, Date range={start_date} to {end_date}")
            
            # Get Polygon API key from lean.json for trading calendar
            lean_config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lean.json")
            with open(lean_config_path, 'r') as f:
                lean_config = json.load(f)
            polygon_api_key = lean_config.get('polygon-api-key', '')
            
            # Check data availability before proceeding with download
            data_available, missing_symbols = self._check_data_availability(symbols, start_date, end_date, polygon_api_key)
            
            # Always download Daily and Minute data, but check Seconds data availability
            self.logs.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "message": "📊 [DATA DOWNLOAD] Daily and Minute data will always be downloaded for latest updates",
                "phase": "data_download"
            })
            
            if data_available:
                # All seconds data is available, but still download daily/minute
                self.logs.append({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "message": "✅ [DATA CHECK] All required Seconds data is available - will download Daily/Minute only",
                    "phase": "data_download"
                })
                backtest_logger.info("✅ DATA CHECK: Seconds data available - downloading Daily/Minute for updates")
                should_download = True  # Changed: always download for daily/minute
                download_symbols = []  # No seconds download needed
                
                # Continue to download phase for daily/minute data
                
            else:
                # Some seconds data is missing, need to download all resolutions including missing symbols
                self.logs.append({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "message": f"⬇️ [DATA CHECK] Will download Daily/Minute for all symbols + Seconds data for {len(missing_symbols)} missing symbols: {', '.join(missing_symbols)}",
                    "phase": "data_download"
                })
                backtest_logger.info(f"⬇️ DATA CHECK: Full download required - Daily/Minute for all, Seconds for {len(missing_symbols)} symbols: {missing_symbols}")
                should_download = True
                download_symbols = missing_symbols
            
        except Exception as e:
            self.logs.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "message": f"❌ [DATA DOWNLOAD] Failed to load config: {e}",
                "phase": "data_download"
            })
            backtest_logger.error(f"❌ DATA DOWNLOAD: Config loading failed: {e}")
            # Config is required - fail the backtest
            self.status = "error"
            return {"error": f"Configuration is required but failed to load: {str(e)}"}

        # Check global flag to disable data downloads
        if DISABLE_DATA_DOWNLOAD:
            self.logs.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "message": "🚫 [DATA DOWNLOAD] Data download globally disabled - using only local data",
                "phase": "data_download"
            })
            backtest_logger.info("🚫 DATA DOWNLOAD: Globally disabled - skipping all downloads")
            should_download = False
        
        # Download required data using Polygon API before backtest (only if needed)
        if should_download:
            self.logs.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "message": "🚀 [DATA DOWNLOAD] Starting download process...",
                "phase": "data_download"
            })
            backtest_logger.info("🚀 DATA DOWNLOAD: Starting download process")
        
        try:
            if should_download:
                # Convert date format for lean command (YYYYMMDD)
                start_date_formatted = start_date.replace('-', '')
                end_date_formatted = end_date.replace('-', '')
                
                # Calculate extended date range for Daily and Minute data (1 year before start date)
                from dateutil.relativedelta import relativedelta
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                extended_start_date_obj = start_date_obj - relativedelta(years=1)
                extended_start_date_formatted = extended_start_date_obj.strftime('%Y%m%d')
                
                # API key already loaded above for trading calendar
            
            if should_download and polygon_api_key:
                # Function to batch symbols to avoid command line length issues
                def batch_symbols(symbol_list, batch_size=1):
                    """Split symbols into batches to avoid command line length issues"""
                    for i in range(0, len(symbol_list), batch_size):
                        yield symbol_list[i:i + batch_size]
                
                # Check if we need to batch symbols
                if len(symbols) > 1:
                    self.logs.append({
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "message": f"⬇️ [DATA DOWNLOAD] Large symbol count ({len(symbols)}), will download in batches of 1",
                        "phase": "data_download"
                    })
                    backtest_logger.info(f"⬇️ DATA DOWNLOAD: Batching {len(symbols)} symbols into groups of 1")
                
                self.logs.append({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "message": f"📊 [DATA DOWNLOAD] Daily/Minute: 1 year extended ({extended_start_date_obj.strftime('%Y-%m-%d')} to {end_date})",
                    "phase": "data_download"
                })
                self.logs.append({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "message": f"📊 [DATA DOWNLOAD] Second: Backtest range only ({start_date} to {end_date})",
                    "phase": "data_download"
                })
                backtest_logger.info(f"📊 Daily/Minute data: {extended_start_date_formatted} to {end_date_formatted} (1 year extended)")
                backtest_logger.info(f"📊 Second data: {start_date_formatted} to {end_date_formatted} (backtest range only)")
                
                # Create download commands for each batch
                download_commands = []
                
                # Batch symbols for Daily and Minute downloads
                for batch_num, symbol_batch in enumerate(batch_symbols(symbols), 1):
                    batch_symbols_str = ','.join(symbol_batch)
                    
                    # Daily data command
                    daily_cmd = [
                        "lean", "data", "download",
                        "--data-provider-historical", "Polygon",
                        "--data-type", "Trade",
                        "--resolution", "Daily",
                        "--security-type", "Equity",
                        "--ticker", batch_symbols_str,
                        "--start", extended_start_date_formatted,
                        "--end", end_date_formatted,
                        "--polygon-api-key", polygon_api_key,
                        "--no-update"
                    ]
                    download_commands.append((f"Daily-Batch{batch_num}", daily_cmd))
                    
                    # Minute data command
                    minute_cmd = [
                        "lean", "data", "download",
                        "--data-provider-historical", "Polygon",
                        "--data-type", "Trade",
                        "--resolution", "Minute",
                        "--security-type", "Equity",
                        "--ticker", batch_symbols_str,
                        "--start", extended_start_date_formatted,
                        "--end", end_date_formatted,
                        "--polygon-api-key", polygon_api_key,
                        "--no-update"
                    ]
                    download_commands.append((f"Minute-Batch{batch_num}", minute_cmd))
                
                # Batch symbols for Second downloads (only missing symbols)
                if download_symbols:
                    for batch_num, symbol_batch in enumerate(batch_symbols(download_symbols), 1):
                        batch_symbols_str = ','.join(symbol_batch)
                        
                        second_cmd = [
                            "lean", "data", "download",
                            "--data-provider-historical", "Polygon",
                            "--data-type", "Trade",
                            "--resolution", "Second",
                            "--security-type", "Equity",
                            "--ticker", batch_symbols_str,
                            "--start", start_date_formatted,
                            "--end", end_date_formatted,
                            "--polygon-api-key", polygon_api_key,
                            "--no-update"
                        ]
                        download_commands.append((f"Second-Batch{batch_num}", second_cmd))
                
                # Track download timing
                self.download_start_time = datetime.now()
                
                total_downloads = len(download_commands)
                all_downloads_successful = True
                failed_resolutions = []
                
                self.logs.append({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "message": f"📊 [DATA DOWNLOAD] Total download tasks: {total_downloads} (in batches of 5 symbols)",
                    "phase": "data_download"
                })
                backtest_logger.info(f"📊 DATA DOWNLOAD: Starting {total_downloads} download tasks")
                
                for step_num, (resolution, cmd) in enumerate(download_commands, 1):
                    # Extract symbols from the command for clearer logging
                    ticker_index = cmd.index("--ticker") + 1 if "--ticker" in cmd else -1
                    symbols_in_batch = cmd[ticker_index] if ticker_index > 0 else "Unknown"
                    
                    # Update download progress
                    self.download_progress = {
                        "current_step": step_num,
                        "total_steps": total_downloads,
                        "current_resolution": resolution,
                        "current_symbols": symbols_in_batch
                    }
                    
                    self.logs.append({
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "message": f"⏱️ [DATA DOWNLOAD] Step {step_num}/{total_downloads}: {resolution} - Symbols: {symbols_in_batch}",
                        "phase": "data_download"
                    })
                    backtest_logger.info(f"⏱️ DATA DOWNLOAD: Step {step_num}/{total_downloads} - {resolution}: {' '.join(cmd)}")
                    
                    # Handle market selection for each download
                    download_process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
                    
                    # Automatically select 'usa' market
                    stdout, _ = download_process.communicate(input="usa\n")  # Mark stderr as intentionally unused
                    
                    if download_process.returncode != 0:
                        all_downloads_successful = False
                        failed_resolutions.append(resolution)
                        self.logs.append({
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                            "message": f"❌ [DATA DOWNLOAD] {resolution} download failed: {stdout}",
                            "phase": "data_download"
                        })
                        backtest_logger.error(f"❌ DATA DOWNLOAD: {resolution} failed: {stdout}")
                    else:
                        self.logs.append({
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                            "message": f"✅ [DATA DOWNLOAD] {resolution} download completed successfully",
                            "phase": "data_download"
                        })
                        backtest_logger.info(f"✅ DATA DOWNLOAD: {resolution} completed successfully")
                
                # Clear download process reference and progress
                self.download_process = None
                self.download_progress = {}  # Clear progress after completion
                
                self.download_end_time = datetime.now()
                download_duration = (self.download_end_time - self.download_start_time).total_seconds()
                
                if all_downloads_successful:
                    self.logs.append({
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "message": f"✅ [DATA DOWNLOAD] All downloads completed successfully in {download_duration:.1f}s",
                        "phase": "data_download"
                    })
                    backtest_logger.info(f"✅ DATA DOWNLOAD: All downloads completed successfully in {download_duration:.1f}s")
                else:
                    self.logs.append({
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "message": f"❌ [DATA DOWNLOAD] Download failed after {download_duration:.1f}s - Failed resolutions: {', '.join(failed_resolutions)}",
                        "phase": "data_download"
                    })
                    backtest_logger.error(f"❌ DATA DOWNLOAD: Failed after {download_duration:.1f}s. Failed resolutions: {', '.join(failed_resolutions)}")
                    
                    # Set error status and stop the backtest
                    self.status = "error"
                    self.end_time = datetime.now()
                    return {"error": f"Data download failed for resolutions: {', '.join(failed_resolutions)}"}
            elif should_download and not polygon_api_key:
                self.logs.append({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "message": "⚠️ [DATA DOWNLOAD] No Polygon API key found, cannot download missing data",
                    "phase": "data_download"
                })
                backtest_logger.warning("⚠️ DATA DOWNLOAD: No Polygon API key found, cannot download missing data")
            elif not should_download:
                self.logs.append({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "message": "⏭️ [DATA DOWNLOAD] Skipping download - all data available locally",
                    "phase": "data_download"
                })
                backtest_logger.info("⏭️ DATA DOWNLOAD: Skipping download phase")
                
        except Exception as e:
            self.logs.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "message": f"❌ [DATA DOWNLOAD] Data download failed: {e}",
                "phase": "data_download"
            })
            backtest_logger.error(f"❌ DATA DOWNLOAD: Download process failed: {e}")

        # Check if operation was cancelled before proceeding to backtest execution
        if self.status == "cancelled":
            backtest_logger.info("🛑 Operation was cancelled during download phase, skipping backtest execution")
            return {"success": "Operation cancelled", "status": "cancelled"}
        
        # Only do phase transition if we haven't already transitioned (i.e., data was missing and downloaded)
        if self.status == "downloading_data":
            # Mark data download phase complete and transition to backtest execution
            self.data_download_time = datetime.now()
            data_download_duration = self.data_download_time - self.start_time
            
            self.logs.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "message": f"✅ [DATA DOWNLOAD] Phase completed in {data_download_duration.total_seconds():.1f}s",
                "phase": "data_download"
            })
            backtest_logger.info(f"✅ DATA DOWNLOAD PHASE COMPLETE: Total duration {data_download_duration.total_seconds():.1f}s")
            
            # Breakdown timing details
            if hasattr(self, 'download_start_time') and hasattr(self, 'download_end_time'):
                actual_download_time = (self.download_end_time - self.download_start_time).total_seconds()
                overhead_time = data_download_duration.total_seconds() - actual_download_time
                backtest_logger.info(f"📊 TIMING BREAKDOWN: Data check + setup: {overhead_time:.1f}s, Actual download: {actual_download_time:.1f}s")
            
            # Transition to backtest execution phase
            self.status = "running_backtest"
            self.phase = "backtest_execution"
            self.backtest_start_time = datetime.now()
            
            self.logs.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "message": "🚀 [BACKTEST EXECUTION] Starting backtest execution phase",
                "phase": "backtest_execution"
            })
            backtest_logger.info(f"🏁 PHASE 2: BACKTEST EXECUTION - Starting backtest at {self.backtest_start_time}")
        
        # Final cancellation check before starting Lean execution
        if self.status == "cancelled":
            backtest_logger.info("🛑 Operation was cancelled, aborting backtest execution")
            return {"success": "Operation cancelled", "status": "cancelled"}
        
        # Start Lean execution
        try:
            self._start_lean_execution(algorithm_name, config_params)
            # Method now runs in background thread, no return needed
            backtest_logger.info(f"🏆 Backtest execution completed successfully for {algorithm_name}")
            
        except Exception as e:
            self.status = "error"
            self.end_time = datetime.now()
            self.logs.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "message": f"❌ [ERROR] Failed to start backtest: {str(e)}",
                "phase": "error"
            })
            backtest_logger.error(f"❌ Failed to start backtest: {str(e)}")
            raise  # Re-raise for the async wrapper to catch
    
    def stop_docker_containers(self):
        """Stop any running Lean Docker containers"""
        try:
            # Get list of running containers with names starting with 'lean'
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}", "--filter", "name=lean"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                container_names = result.stdout.strip().split('\n')
                for container_name in container_names:
                    if container_name:
                        backtest_logger.info(f"🐳 Stopping Docker container: {container_name}")
                        subprocess.run(
                            ["docker", "stop", container_name],
                            capture_output=True,
                            timeout=10
                        )
                        backtest_logger.info(f"✅ Docker container {container_name} stopped")
                return True
        except subprocess.TimeoutExpired:
            backtest_logger.error("⏱️ Timeout while stopping Docker containers")
        except FileNotFoundError:
            backtest_logger.warning("⚠️ Docker command not found - skipping container cleanup")
        except Exception as e:
            backtest_logger.error(f"❌ Error stopping Docker containers: {e}")
        return False

    def stop_backtest(self):
        """Stop the running backtest or data download"""
        stopped_something = False
        
        # Check if data download is running
        if self.download_process and self.download_process.poll() is None:
            try:
                backtest_logger.info("🛑 Stopping data download process...")
                self.download_process.terminate()
                
                # Wait up to 5 seconds for graceful exit
                try:
                    self.download_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.download_process.kill()
                    self.download_process.wait()
                
                self.download_process = None
                stopped_something = True
                
                self.logs.append({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "message": "🛑 [DATA DOWNLOAD] Download cancelled by user",
                    "phase": "data_download"
                })
                backtest_logger.info("🛑 Data download cancelled by user")
                
            except Exception as e:
                backtest_logger.error(f"❌ Failed to stop download process: {e}")
        
        # Check if backtest is running
        if self.process and self.process.poll() is None:
            try:
                backtest_logger.info("🛑 Stopping backtest process...")
                # Try graceful termination first
                self.process.terminate()
                
                # Wait up to 5 seconds for graceful exit
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't exit gracefully
                    self.process.kill()
                    self.process.wait()
                
                stopped_something = True
                backtest_logger.info("🛑 Backtest stopped successfully")
                
                # Also stop any Docker containers that Lean might have spawned
                self.stop_docker_containers()
                
            except Exception as e:
                backtest_logger.error(f"❌ Failed to stop backtest: {e}")
                return {"error": f"Failed to stop backtest: {str(e)}"}
        
        # Even if no process is running, check for orphaned Docker containers
        if not stopped_something:
            if self.stop_docker_containers():
                stopped_something = True
                backtest_logger.info("🐳 Cleaned up orphaned Docker containers")
        
        if stopped_something:
            self.status = "cancelled"
            self.phase = None  # Clear phase so frontend shows "Cancelled" instead of phase-specific text
            self.end_time = datetime.now()
            return {"success": "Operation stopped"}
        else:
            return {"error": "No operation running to stop"}
    
    def get_status(self):
        """Get current backtest status"""
        if self.process:
            poll_result = self.process.poll()
            if poll_result is not None and self.status in ["running_backtest"]:
                self.status = "completed" if poll_result == 0 else "error"
                self.end_time = datetime.now()
                self.phase = None
                
                if self.status == "completed":
                    backtest_logger.info("🏆 BACKTEST EXECUTION COMPLETED: Process finished successfully")
                    self._find_latest_results()
                else:
                    backtest_logger.error("❌ BACKTEST EXECUTION FAILED: Process returned error")
        
        # Calculate phase-specific durations
        status_info = {
            "status": self.status,
            "phase": self.phase,
            "pid": self.process.pid if self.process else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "log_count": len(self.logs)
        }
        
        # Add download-specific information when in download phase
        if self.status == "downloading_data" and self.download_symbols:
            status_info["download_info"] = {
                "symbols": self.download_symbols,
                "date_range": self.download_date_range,
                "progress": self.download_progress
            }
        
        # Add phase-specific timing information
        if self.start_time:
            if self.data_download_time:
                status_info["data_download_duration"] = f"{(self.data_download_time - self.start_time).total_seconds():.1f}s"
            
            if self.backtest_start_time:
                status_info["backtest_start_time"] = self.backtest_start_time.isoformat()
                if self.end_time:
                    status_info["backtest_duration"] = f"{(self.end_time - self.backtest_start_time).total_seconds():.1f}s"
            
            if self.end_time:
                status_info["total_duration"] = f"{(self.end_time - self.start_time).total_seconds():.1f}s"
        
        return status_info
    
    def get_logs(self, last_n=50):
        """Get recent log entries"""
        return {
            "logs": self.logs[-last_n:] if self.logs else [],
            "total_count": len(self.logs)
        }
    
    def _monitor_logs(self):
        """Monitor backtest output in a separate thread"""
        if not self.process:
            return
        
        try:
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    log_entry = {
                        "timestamp": timestamp,
                        "message": f"[BACKTEST EXECUTION] {line.strip()}",
                        "phase": "backtest_execution"
                    }
                    self.logs.append(log_entry)
                    
                    # Log to backtest logger as well
                    backtest_logger.info(f"LEAN OUTPUT: {line.strip()}")
                    
                    # Keep only last 1000 log entries to prevent memory issues
                    if len(self.logs) > 1000:
                        self.logs = self.logs[-1000:]
                
                # Check if process ended
                if self.process.poll() is not None:
                    break
            
            # Process has ended - update status
            if self.process.poll() is not None:
                exit_code = self.process.poll()
                if exit_code == 0:
                    self.status = "completed"
                    self.logs.append({
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "message": "✅ [BACKTEST EXECUTION] Backtest completed successfully",
                        "phase": "backtest_execution"
                    })
                    backtest_logger.info("✅ BACKTEST EXECUTION: Process completed successfully")
                else:
                    self.status = "error"
                    self.logs.append({
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "message": f"❌ [BACKTEST EXECUTION] Backtest failed with exit code {exit_code}",
                        "phase": "error"
                    })
                    backtest_logger.error(f"❌ BACKTEST EXECUTION: Process failed with exit code {exit_code}")
                
                self.end_time = datetime.now()
                self._find_latest_results()
                    
        except Exception as e:
            self.logs.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "message": f"Log monitoring error: {str(e)}"
            })
    
    def _find_latest_results(self):
        """Find the latest backtest results JSON file"""
        global latest_results_path
        try:
            import glob
            import os
            
            # Look for main Lean results files first (not order-events or summary files)
            main_results_pattern = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ZacQC/backtests/*/[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].json")
            test_results_pattern = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ZacQC/backtests/*/test_*.json")
            
            # Prioritize main Lean results files
            main_files = glob.glob(main_results_pattern)
            test_files = glob.glob(test_results_pattern)
            
            json_files = main_files + test_files  # Main results first
            
            if json_files:
                # Get the most recent file by modification time
                latest_file = max(json_files, key=os.path.getmtime)
                latest_results_path = latest_file
                self.logs.append({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "message": f"Found backtest results: {latest_file}"
                })
            else:
                self.logs.append({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "message": "No backtest results found"
                })
        except Exception as e:
            self.logs.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "message": f"Error finding results: {str(e)}"
            })

# Initialize backtest manager
backtest_manager = BacktestManager()

# API Routes
@app.route('/api/backtest/start', methods=['POST'])
def start_backtest():
    """Start a new backtest"""
    logger.info("🚀 API: /api/backtest/start endpoint called")
    
    data = request.get_json() or {}
    algorithm = data.get('algorithm', 'ZacQC')
    config_params = data.get('config_params', {})
    
    logger.info(f"📊 API: Starting backtest with algorithm={algorithm}, config_params={config_params}")
    
    result = backtest_manager.start_backtest(algorithm, config_params)
    
    logger.info(f"✅ API: Backtest start result: {result}")
    return jsonify(result)

@app.route('/api/backtest/stop', methods=['POST'])
def stop_backtest():
    """Stop the running backtest"""
    logger.info("🛑 API: /api/backtest/stop endpoint called")
    
    result = backtest_manager.stop_backtest()
    
    logger.info(f"✅ API: Backtest stop result: {result}")
    return jsonify(result)

@app.route('/api/backtest/status', methods=['GET'])
def get_status():
    """Get backtest status"""
    logger.debug("📋 API: /api/backtest/status endpoint called")
    
    status = backtest_manager.get_status()
    
    phase_info = f" | Phase: {status.get('phase', 'None')}" if status.get('phase') else ""
    logger.debug(f"📋 API: Status response: {status['status']}{phase_info} (pid: {status.get('pid', 'None')})")
    return jsonify(status)

@app.route('/api/backtest/logs', methods=['GET'])
def get_logs():
    """Get backtest logs"""
    last_n = request.args.get('last_n', 50, type=int)
    logs = backtest_manager.get_logs(last_n)
    return jsonify(logs)

@app.route('/api/backtest/results', methods=['GET'])
def get_results():
    """Get latest backtest results"""
    global latest_results_path
    
    # Force a scan for results if none found
    if not latest_results_path:
        backtest_manager._find_latest_results()
    
    if not latest_results_path or not os.path.exists(latest_results_path):
        return jsonify({"error": "No results available"}), 404
    
    try:
        with open(latest_results_path, 'r') as f:
            results = json.load(f)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": f"Failed to load results: {str(e)}"}), 500

@app.route('/api/backtest/scan-results', methods=['POST'])
def scan_results():
    """Manually scan for backtest results"""
    backtest_manager._find_latest_results()
    global latest_results_path
    
    if latest_results_path:
        return jsonify({"success": f"Found results: {latest_results_path}"})
    else:
        return jsonify({"error": "No results found"}), 404

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/api/data-download/status', methods=['GET'])
def get_data_download_status():
    """Get current data download setting"""
    global DISABLE_DATA_DOWNLOAD
    return jsonify({
        "disabled": DISABLE_DATA_DOWNLOAD,
        "message": "Data downloads are globally disabled" if DISABLE_DATA_DOWNLOAD else "Data downloads are enabled"
    })

@app.route('/api/data-download/disable', methods=['POST'])
def disable_data_download():
    """Disable all data downloads globally"""
    global DISABLE_DATA_DOWNLOAD
    DISABLE_DATA_DOWNLOAD = True
    logger.info("🚫 API: Data downloads globally disabled")
    return jsonify({
        "success": True,
        "message": "Data downloads globally disabled",
        "disabled": True
    })

@app.route('/api/data-download/enable', methods=['POST'])
def enable_data_download():
    """Enable data downloads globally"""
    global DISABLE_DATA_DOWNLOAD
    DISABLE_DATA_DOWNLOAD = False
    logger.info("✅ API: Data downloads globally enabled")
    return jsonify({
        "success": True,
        "message": "Data downloads globally enabled",
        "disabled": False
    })

# Configuration API Routes
@app.route('/api/config', methods=['GET'])
def get_config():
    """Load and return the current configuration"""
    logger.info("⚙️ API: /api/config GET endpoint called")
    
    try:
        # Load configuration from parameters.py
        config_dict = load_config_strict(CONFIG_FILE_PATH)
        
        logger.info(f"✅ API: Configuration loaded successfully ({len(config_dict)} parameters)")
        return jsonify(config_dict)
        
    except Exception as e:
        logger.error(f"❌ API: Failed to load configuration: {str(e)}")
        return jsonify({"error": f"Failed to load configuration: {str(e)}"}), 500

@app.route('/api/config', methods=['POST'])
def save_config():
    """Save configuration to file with strict validation"""
    logger.info("💾 API: /api/config POST endpoint called")
    
    try:
        config_data = request.get_json()
        if not config_data:
            logger.warning("❌ API: No configuration data provided")
            return jsonify({"error": "No configuration data provided"}), 400
        
        logger.info(f"📊 API: Saving configuration with {len(config_data)} parameters")
        
        # Debug boolean values
        for key, value in config_data.items():
            if key in ['Allow_Actions', 'C1', 'C2', 'C3', 'C4', 'C5']:
                logger.info(f"DEBUG: {key} = {value} (type: {type(value).__name__})")
        
        # Save directly to parameters.py
        success = save_config_to_parameters_py(config_data, CONFIG_FILE_PATH)
        
        if not success:
            return jsonify({"error": "Failed to save configuration to parameters.py"}), 500
        
        # Validate by trying to reload
        try:
            _ = load_config_strict(CONFIG_FILE_PATH)  # Validate config structure
            logger.info("✅ API: Configuration validation passed")
        except Exception as validation_error:
            logger.error(f"❌ API: Configuration validation failed: {str(validation_error)}")
            return jsonify({"error": f"Configuration validation failed: {str(validation_error)}"}), 400
        
        logger.info(f"✅ API: Configuration saved successfully to {CONFIG_FILE_PATH}")
        
        return jsonify({"message": "Configuration saved successfully"})
        
    except Exception as e:
        logger.error(f"❌ API: Failed to save configuration: {str(e)}")
        return jsonify({"error": f"Failed to save configuration: {str(e)}"}), 500

@app.route('/api/config/validate', methods=['GET'])
def validate_config():
    """Validate the current configuration file"""
    try:
        config_dict = load_config_strict(CONFIG_FILE_PATH)
        
        # Count parameters
        param_count = len(config_dict)
        
        return jsonify({
            "valid": True,
            "message": "Configuration is valid",
            "parameter_count": param_count
        })
        
    except Exception as e:
        return jsonify({
            "valid": False,
            "message": f"Configuration validation failed: {str(e)}",
            "parameter_count": 0
        })

# Frontend routes
@app.route('/')
def index():
    """Serve the new homepage"""
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')
    response = send_file(os.path.join(frontend_dir, 'index.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/config')
def config_page():
    """Serve the configuration editor"""
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')
    return send_file(os.path.join(frontend_dir, 'config_editor.html'))

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files from frontend directory"""
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')
    return send_from_directory(frontend_dir, filename)


if __name__ == '__main__':
    # Only run port cleanup in the main process (not reloader)
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        # Clean up any existing processes on port 5001
        kill_process_on_port(5001)
        print("🚀 Starting Backtest Control Server...")
        print("🌐 Access the web interface at: http://localhost:5001")
        print(f"📁 Log files located in: {LOG_DIR}")
        print("📝 Available log files:")
        print("   - backtest_server.log (Main server operations)")
        print("   - request_processing.log (HTTP request details)")
        print("   - backtest_execution.log (Backtest process logs)")
        print("   - flask_requests.log (Flask HTTP requests)")
        logger.info("🚀 Backtest Control Server starting up")
        logger.info(f"📁 Comprehensive logging enabled, logs directory: {LOG_DIR}")
        logger.info(f"📊 Data download status: {'DISABLED' if DISABLE_DATA_DOWNLOAD else 'ENABLED'}")
    
    app.run(debug=True, host='0.0.0.0', port=8080, use_reloader=True)