#!/bin/bash
# CleanSight Data Explorer - Mac/Linux Launcher
# Run this file to start the dashboard: ./start_dashboard.sh

echo "============================================================"
echo "  CleanSight Data Explorer"
echo "============================================================"
echo ""

# Check if virtual environment exists
if [ -d "cleansight_env" ]; then
    echo "Activating virtual environment..."
    source cleansight_env/bin/activate
else
    echo "No virtual environment found. Using system Python."
fi

echo ""
echo "Starting dashboard..."
echo ""
echo "Once started, open your browser to: http://localhost:8050"
echo ""
echo "Press Ctrl+C to stop the server."
echo "============================================================"
echo ""

python app.py
