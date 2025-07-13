@echo off
REM Setup script for uv environment on Windows
REM Run this after cloning the repository

echo Setting up doc-converter with uv...

REM Check if uv is installed
uv --version >nul 2>&1
if errorlevel 1 (
    echo uv is not installed. Please install uv first:
    echo   winget install --id=astral-sh.uv -e
    echo   or: pip install uv
    pause
    exit /b 1
)

echo uv version:
uv --version

REM Create virtual environment and install dependencies
echo Creating virtual environment and installing dependencies...
uv sync

REM Install development dependencies
echo Installing development dependencies...
uv sync --dev

echo Setup complete!
echo.
echo To activate the virtual environment:
echo   .venv\Scripts\activate
echo.
echo To run the application:
echo   uv run python run_api.py
echo   uv run python run_worker.py
echo.
echo To run tests:
echo   uv run pytest tests/ -v

pause