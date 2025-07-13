# Development Setup with uv

This project uses [uv](https://docs.astral.sh/uv/) for fast Python package management and virtual environment handling.

## Install uv

### Windows
```bash
# Using pip
pip install uv

# Using pipx (recommended)
pipx install uv

# Using winget
winget install --id=astral-sh.uv  -e
```

### Linux/macOS
```bash
# Using pip
pip install uv

# Using pipx (recommended)
pipx install uv

# Using curl
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Project Setup

1. **Clone and enter the project directory:**
```bash
git clone <repository-url>
cd doc_converter
```

2. **Create virtual environment and install dependencies:**
```bash
# This creates .venv and installs all dependencies
uv sync
```

3. **Activate the virtual environment:**
```bash
# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate
```

4. **Install development dependencies:**
```bash
uv sync --dev
```

## Development Commands

### Adding Dependencies
```bash
# Add a runtime dependency
uv add fastapi

# Add a development dependency
uv add --dev pytest

# Add with version constraint
uv add "pydantic>=2.0.0"
```

### Running the Application
```bash
# Run API server
uv run python run_api.py

# Run Celery worker (try these in order if one fails)
uv run python run_worker.py          # Method 1 (recommended)
uv run python run_worker_cli.py      # Method 2 (if Method 1 fails)

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=src
```

### Troubleshooting Celery Worker

If the worker fails to start, try these alternatives:

1. **Direct celery command:**
```bash
# Windows
set PYTHONPATH=src
uv run celery -A src.services.celery_app:celery_app worker --loglevel=INFO --pool=solo --concurrency=1

# Linux/macOS
export PYTHONPATH=src
uv run celery -A src.services.celery_app:celery_app worker --loglevel=INFO --pool=prefork --concurrency=4
```

2. **Check celery_commands.md** for more options and troubleshooting tips.

### Code Quality
```bash
# Format code
uv run black src/ tests/

# Lint code
uv run flake8 src/ tests/

# Type checking
uv run mypy src/
```

### Updating Dependencies
```bash
# Update all dependencies to latest compatible versions
uv lock --upgrade

# Sync environment with updated lockfile
uv sync
```

## Environment Management

uv automatically manages your virtual environment:

- **Virtual environment**: `.venv/` (automatically created)
- **Lock file**: `uv.lock` (commit this to version control)
- **Python version**: Specified in `.python-version`

## Docker Development

The Dockerfile has been updated to use uv for faster dependency installation.