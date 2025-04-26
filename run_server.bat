@echo off
:: Simple script to run the Linear MCP server on Windows

:: Activate virtual environment if it exists
IF EXIST venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

:: Check for requirements installation
python -c "import fastapi" 2>NUL
IF %ERRORLEVEL% NEQ 0 (
    echo Installing dependencies...
    pip install -r requirements.txt
)

:: Run the server
echo Starting Linear MCP server...
python -m src.main --env-file .env

:: Deactivate virtual environment on exit
IF EXIST venv\Scripts\activate.bat (
    call venv\Scripts\deactivate.bat
)