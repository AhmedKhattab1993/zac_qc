#!/usr/bin/env python3
"""
Start the backtest server in production mode
"""
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the server
from server.backtest_server import app

if __name__ == '__main__':
    print("🚀 Starting Backtest Control Server in production mode...")
    print("🌐 Access the web interface at: http://localhost:8080")
    print("📍 For external access use: http://YOUR_PUBLIC_IP:8080")
    # Run without debug mode for background execution
    app.run(debug=False, host='0.0.0.0', port=8080, use_reloader=False)