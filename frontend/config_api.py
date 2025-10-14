"""
Simplified Config API Server for Reference ZacQC Configuration Editor
Provides REST endpoints to save/load configuration directly from parameters.py
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import json
import os
import re
from typing import Dict, Any

app = FastAPI(title="Strategy Configuration API", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration file path - now points to parameters.py
PARAMETERS_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ZacQC", "config", "parameters.py")

# Mount static files (serve JS and other assets)
frontend_dir = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

# Serve config_editor.js directly from root
@app.get("/config_editor.js")
async def get_config_js():
    """Serve the config editor JavaScript file"""
    js_path = os.path.join(frontend_dir, "config_editor.js")
    return FileResponse(js_path, media_type="application/javascript")

@app.get("/")
async def root():
    """Serve the main homepage with backtest controls"""
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    return FileResponse(html_path)

@app.get("/config")
async def config_page():
    """Serve the configuration editor HTML page"""
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_editor.html")
    return FileResponse(html_path)

@app.get("/api/config")
async def get_config() -> Dict[str, Any]:
    """
    Load and return the current configuration from parameters.py
    """
    try:
        if not os.path.exists(PARAMETERS_FILE_PATH):
            raise HTTPException(status_code=404, detail="Parameters file not found")
        
        # Read the parameters.py file and extract values
        with open(PARAMETERS_FILE_PATH, 'r') as f:
            content = f.read()
        
        # Extract parameter values using regex
        def extract_value(param_name):
            pattern = rf"self\.{param_name}\s*=\s*(.+?)#"
            match = re.search(pattern, content)
            if match:
                value_str = match.group(1).strip()
                # Handle different types
                if value_str in ['True', 'False']:
                    return value_str == 'True'
                elif value_str.startswith('[') and value_str.endswith(']'):
                    return eval(value_str)  # For lists like ['AAPL', 'TSLA']
                elif value_str.startswith('"') and value_str.endswith('"'):
                    return value_str[1:-1]  # Remove quotes
                elif '.' in value_str:
                    return float(value_str)
                else:
                    return int(value_str)
            return None
        
        # Extract all parameters
        config_data = {
            # Core Trading Parameters
            "Parameter_1": extract_value("Parameter_1") or 30,
            "Parameter_2": extract_value("Parameter_2") or 30,
            "Parameter_3": extract_value("Parameter_3") or 200,
            "Parameter_4": extract_value("Parameter_4") or 8,
            "Parameter_5": extract_value("Parameter_5") or 8,
            
            # Condition Enablement
            "C1": extract_value("C1") if extract_value("C1") is not None else True,
            "C2": extract_value("C2") if extract_value("C2") is not None else True,
            "C3": extract_value("C3") if extract_value("C3") is not None else False,
            "C4": extract_value("C4") if extract_value("C4") is not None else True,
            "C5": extract_value("C5") if extract_value("C5") is not None else True,
            
            # Profit Take Settings
            "ProfitTakeC1": extract_value("ProfitTakeC1") or 15,
            "ProfitTakeC2": extract_value("ProfitTakeC2") or 15,
            "ProfitTakeC3": extract_value("ProfitTakeC3") or 15,
            "ProfitTakeC4": extract_value("ProfitTakeC4") or 15,
            "ProfitTakeC5": extract_value("ProfitTakeC5") or 15,
            
            # Risk Management
            "StopLoss": extract_value("StopLoss") or 500,
            "SharesToSell": extract_value("SharesToSell") or 100,
            "OffsetPCT": extract_value("OffsetPCT") or 0.1,
            
            # Timing Constraints
            "SameSymbolTime": extract_value("SameSymbolTime") or 1,
            "SameConditionTimeC1": extract_value("SameConditionTimeC1") or 1,
            "SameConditionTimeC2": extract_value("SameConditionTimeC2") or 1,
            "SameConditionTimeC3": extract_value("SameConditionTimeC3") or 1,
            "SameConditionTimeC4": extract_value("SameConditionTimeC4") or 1,
            "SameConditionTimeC5": extract_value("SameConditionTimeC5") or 1,
            
            # Stop Loss Update
            "StopLossUpdate": extract_value("StopLossUpdate") or 1,
            
            # Stop Loss X/Y Parameters
            "StopLossXC1": extract_value("StopLossXC1") or 10,
            "StopLossYC1": extract_value("StopLossYC1") or 80,
            "StopLossXC2": extract_value("StopLossXC2") or 10,
            "StopLossYC2": extract_value("StopLossYC2") or 80,
            "StopLossXC3": extract_value("StopLossXC3") or 10,
            "StopLossYC3": extract_value("StopLossYC3") or 80,
            "StopLossXC4": extract_value("StopLossXC4") or 10,
            "StopLossYC4": extract_value("StopLossYC4") or 80,
            "StopLossXC5": extract_value("StopLossXC5") or 10,
            "StopLossYC5": extract_value("StopLossYC5") or 80,
            
            # Capital Management
            "cash_pct": extract_value("cash_pct") or 40,
            "MaxCapitalPCT": extract_value("MaxCapitalPCT") or 225,
            
            # VWAP Settings
            "VWAP_PCT": extract_value("VWAP_PCT") or 10,
            "Vwap_Margin": extract_value("Vwap_Margin") or 20,
            
            # Rally Conditions
            "Rally_X_Min_PCT": extract_value("Rally_X_Min_PCT") or 0.1,
            "Rally_X_Max_PCT": extract_value("Rally_X_Max_PCT") or 50,
            "Rally_Y_PCT": extract_value("Rally_Y_PCT") or 0.1,
            "Rally_Time_Constraint": extract_value("Rally_Time_Constraint") or 30,
            "Rally_Time_Constraint_Threshold": extract_value("Rally_Time_Constraint_Threshold") or 3,
            
            # Action Timing
            "Allow_Actions": extract_value("Allow_Actions") if extract_value("Allow_Actions") is not None else True,
            "Action1_Time": extract_value("Action1_Time") or 1,
            "Action2_Time": extract_value("Action2_Time") or 3,
            
            # Market Hours - extract from time() constructor
            "Algo_Off_Before": "09:30",  # Default
            "Algo_Off_After": "15:50",   # Default
            
            # Daily Limits
            "Max_Daily_PNL": extract_value("Max_Daily_PNL") or 10,
            
            # Advanced Settings
            "New_Range_Order_Cancellation_Margin": extract_value("New_Range_Order_Cancellation_Margin") or 0.5,
            "RangeMultipleThreshold": extract_value("RangeMultipleThreshold") or 5,
            "Liquidity_Threshold": extract_value("Liquidity_Threshold") or 0,
            "Gap_Threshold": extract_value("Gap_Threshold") or 90,
            "SharpMovement_Threshold": extract_value("SharpMovement_Threshold") or 200,
            "SharpMovement_Minutes": extract_value("SharpMovement_Minutes") or 4,
            
            # Frontend parameters
            "symbols": extract_value("symbols") or ['AAPL', 'TSLA'],
            "starting_cash": extract_value("starting_cash") or 50000,
            "start_date": extract_value("start_date") or "2025-05-05",
            "end_date": extract_value("end_date") or "2025-05-20",
            "account_id": extract_value("account_id") or "DU3166840"
        }
        
        # Extract time values
        time_before_match = re.search(r"self\.Algo_Off_Before\s*=\s*time\((\d+),\s*(\d+)\)", content)
        if time_before_match:
            hour, minute = time_before_match.groups()
            config_data["Algo_Off_Before"] = f"{int(hour):02d}:{int(minute):02d}"
            
        time_after_match = re.search(r"self\.Algo_Off_After\s*=\s*time\((\d+),\s*(\d+)\)", content)
        if time_after_match:
            hour, minute = time_after_match.groups()
            config_data["Algo_Off_After"] = f"{int(hour):02d}:{int(minute):02d}"
        
        return config_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load configuration: {str(e)}")

@app.post("/api/config")
async def save_config(config_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Save configuration to parameters.py by updating the hardcoded values
    """
    try:
        # Basic validation - ensure required frontend parameters exist
        required_params = ['symbols', 'starting_cash', 'start_date', 'end_date']
        for param in required_params:
            if param not in config_data:
                raise HTTPException(status_code=400, detail=f"Missing required parameter: {param}")
        
        # Read the current parameters.py file
        with open(PARAMETERS_FILE_PATH, 'r') as f:
            content = f.read()
        
        # Define replacements for all parameters
        def replace_parameter(content, param_name, new_value):
            """Replace a parameter value in the content"""
            if isinstance(new_value, str) and param_name not in ['start_date', 'end_date', 'account_id']:
                # Don't quote non-string parameters
                if param_name in ['symbols']:
                    pattern = rf"(self\.{param_name}\s*=\s*)(.+?)(#.*)"
                    return re.sub(pattern, rf"\1{new_value}\3", content)
                else:
                    pattern = rf"(self\.{param_name}\s*=\s*)(.+?)(#.*)"
                    return re.sub(pattern, rf"\1{new_value}\3", content)
            elif isinstance(new_value, str):
                # Quote string parameters
                pattern = rf"(self\.{param_name}\s*=\s*[\"\'])(.+?)([\"\'].*#.*)"
                return re.sub(pattern, rf"\1{new_value}\3", content)
            elif isinstance(new_value, bool):
                pattern = rf"(self\.{param_name}\s*=\s*)(True|False)(.*)"
                result = re.sub(pattern, rf"\1{new_value}\3", content)
                print(f"DEBUG: Replacing boolean parameter {param_name}: {new_value}")
                print(f"DEBUG: Pattern: {pattern}")
                print(f"DEBUG: Before: {content.count('True')}, After: {result.count('True')}")
                return result
            else:
                # Numeric parameters
                pattern = rf"(self\.{param_name}\s*=\s*)([^#]+)(#.*)"
                return re.sub(pattern, rf"\1{new_value}\3", content)
        
        # Apply all replacements
        updated_content = content
        print(f"DEBUG: Received config data: {config_data}")
        for param_name, new_value in config_data.items():
            if param_name in ['Algo_Off_Before', 'Algo_Off_After']:
                # Handle time parameters
                hour, minute = new_value.split(':')
                time_replacement = f"time({int(hour)}, {int(minute)})"
                pattern = rf"(self\.{param_name}\s*=\s*)(time\(\d+,\s*\d+\))(.*#.*)"
                updated_content = re.sub(pattern, rf"\1{time_replacement}\3", updated_content)
            else:
                updated_content = replace_parameter(updated_content, param_name, new_value)
        
        # Write to temporary file first
        temp_parameters_path = PARAMETERS_FILE_PATH + ".tmp"
        
        with open(temp_parameters_path, 'w') as f:
            f.write(updated_content)
        
        # Move temporary file to final location
        os.rename(temp_parameters_path, PARAMETERS_FILE_PATH)
        
        return {"status": "success", "message": "Configuration saved to parameters.py successfully"}
        
    except Exception as e:
        # Clean up temp file if it exists
        temp_path = PARAMETERS_FILE_PATH + ".tmp"
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        raise HTTPException(status_code=500, detail=f"Failed to save configuration: {str(e)}")

@app.post("/api/backtest/run")
async def run_backtest():
    """Start a new backtest"""
    try:
        import subprocess
        import os
        
        # Change to the parent directory (where lean command should be run)
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Run lean backtest command
        result = subprocess.run(
            ["lean", "backtest", "ZacQC", "--no-update"],
            cwd=parent_dir,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            return {
                "status": "success", 
                "message": "Backtest completed successfully",
                "output": result.stdout
            }
        else:
            return {
                "status": "error", 
                "message": "Backtest failed",
                "error": result.stderr
            }
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "message": "Backtest timed out after 5 minutes"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to run backtest: {str(e)}"
        }

@app.get("/api/backtest/results")
async def get_backtest_results():
    """Get latest backtest results"""
    try:
        import glob
        import json
        
        # Look for the most recent backtest results
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        results_pattern = os.path.join(parent_dir, "ZacQC", "backtests", "*", "*.json")
        result_files = glob.glob(results_pattern)
        
        if not result_files:
            return {"status": "no_results", "message": "No backtest results found"}
        
        # Get the most recent result file
        latest_file = max(result_files, key=os.path.getmtime)
        
        with open(latest_file, 'r') as f:
            result_data = json.load(f)
        
        return {
            "status": "success",
            "file": latest_file,
            "data": result_data
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get results: {str(e)}"
        }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ZacQC Trading System API"}

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.environ.get("PORT", 8000))
    
    print(f"🚀 Starting Configuration API on port {port}")
    print(f"📁 Parameters file: {PARAMETERS_FILE_PATH}")
    print(f"🌐 Open browser to: http://localhost:{port}")
    
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")