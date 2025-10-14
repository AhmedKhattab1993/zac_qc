#!/bin/bash

# Setup script for the backtest server systemd service

echo "🔧 Setting up Backtest Server as a system service..."

# Check if running with sudo
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run with sudo" 
   echo "   Usage: sudo ./setup-service.sh"
   exit 1
fi

# Copy the service file to systemd directory
echo "📋 Copying service file to systemd..."
cp /home/cloudibkr/Documents/zac_qc/backtest-server.service /etc/systemd/system/

# Reload systemd to recognize the new service
echo "🔄 Reloading systemd daemon..."
systemctl daemon-reload

# Enable the service to start on boot
echo "🚀 Enabling service to start on boot..."
systemctl enable backtest-server.service

# Start the service
echo "▶️  Starting the service..."
systemctl start backtest-server.service

# Check service status
echo "📊 Checking service status..."
systemctl status backtest-server.service --no-pager

echo ""
echo "✅ Setup complete!"
echo ""
echo "📌 Useful commands:"
echo "   - Check status:  sudo systemctl status backtest-server"
echo "   - Stop service:  sudo systemctl stop backtest-server"
echo "   - Start service: sudo systemctl start backtest-server"
echo "   - Restart:       sudo systemctl restart backtest-server"
echo "   - View logs:     sudo journalctl -u backtest-server -f"
echo "   - Disable:       sudo systemctl disable backtest-server"