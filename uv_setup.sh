#!/bin/bash

# Setup script for uv environment
# Run this after cloning the repository

echo "Setting up doc-converter with uv..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Installing uv..."
    
    # Detect OS and install uv
    if [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "darwin"* ]]; then
        # Linux or macOS
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$PATH"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        # Windows
        echo "Please install uv manually:"
        echo "  winget install --id=astral-sh.uv -e"
        echo "  or: pip install uv"
        exit 1
    fi
fi

echo "uv version: $(uv --version)"

# Create virtual environment and install dependencies
echo "Creating virtual environment and installing dependencies..."
uv sync

# Install development dependencies
echo "Installing development dependencies..."
uv sync --dev

echo "Setup complete!"
echo ""
echo "To activate the virtual environment:"
echo "  source .venv/bin/activate  # Linux/macOS"
echo "  .venv\\Scripts\\activate     # Windows"
echo ""
echo "To run the application:"
echo "  uv run python run_api.py"
echo "  uv run python run_worker.py"
echo ""
echo "To run tests:"
echo "  uv run pytest tests/ -v"