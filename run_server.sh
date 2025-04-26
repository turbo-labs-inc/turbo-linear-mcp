#!/bin/bash
# Simple script to run the Linear MCP server

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check for requirements installation
if ! python -c "import fastapi" &> /dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Run the server
echo "Starting Linear MCP server..."
python -m src.main --env-file .env

# Deactivate virtual environment on exit
if [ -d "venv" ]; then
    deactivate
fi