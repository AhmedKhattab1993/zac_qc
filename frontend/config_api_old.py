"""
Simplified Config API Server for Reference ZacQC Configuration Editor
Provides REST endpoints to save/load configuration
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import json
import os
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

# Configuration file path
CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "config.json")

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
    Load and return the current configuration
    """
    try:
        # Load configuration from JSON file
        if not os.path.exists(CONFIG_FILE_PATH):
            raise HTTPException(status_code=404, detail="Configuration file not found")
        
        with open(CONFIG_FILE_PATH, 'r') as f:
            config_data = json.load(f)
        
        return config_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load configuration: {str(e)}")

@app.post("/api/config")
async def save_config(config_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Save configuration to file
    """
    try:
        # Basic validation - ensure required frontend parameters exist
        required_params = ['symbols', 'starting_cash', 'start_date', 'end_date']
        for param in required_params:
            if param not in config_data:
                raise HTTPException(status_code=400, detail=f"Missing required parameter: {param}")
        
        # Write to temporary file first
        temp_config_path = CONFIG_FILE_PATH + ".tmp"
        
        with open(temp_config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        # Move temporary file to final location
        os.rename(temp_config_path, CONFIG_FILE_PATH)
        
        return {"status": "success", "message": "Configuration saved successfully"}
        
    except Exception as e:
        # Clean up temp file if it exists
        temp_path = CONFIG_FILE_PATH + ".tmp"
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
            ["lean", "backtest", "ZacQC"],
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
    print(f"📁 Config file: {CONFIG_FILE_PATH}")
    print(f"🌐 Open browser to: http://localhost:{port}")
    
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")