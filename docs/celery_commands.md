# Celery Commands

## Running the Worker

### Method 1: Using the Python script (recommended)
```bash
python run_worker.py
```

### Method 2: Using CLI script (if Method 1 fails)
```bash
python run_worker_cli.py
```

### Method 3: Direct Celery command
```bash
# Set PYTHONPATH first
set PYTHONPATH=src  # Windows
export PYTHONPATH=src  # Linux/macOS

# Run worker (Windows)
celery -A src.services.celery_app:celery_app worker --loglevel=INFO --pool=solo --concurrency=1

# Run worker (Linux/macOS - can use threads for better async support)
celery -A src.services.celery_app:celery_app worker --loglevel=INFO --pool=threads --concurrency=4
```

### Method 4: Using uv (if using uv)
```bash
uv run python run_worker.py
```

## Windows Specific Notes

- Use `--pool=solo` for Windows compatibility
- Prefork pool doesn't work well on Windows
- Solo pool is recommended for development

## Linux/macOS Options

You can use different pools on Unix systems:
```bash
# Prefork (default)
celery -A src.services.celery_app:celery_app worker --loglevel=INFO --pool=prefork --concurrency=4

# Eventlet (for I/O bound tasks)
celery -A src.services.celery_app:celery_app worker --loglevel=INFO --pool=eventlet --concurrency=100

# Gevent (alternative to eventlet)
celery -A src.services.celery_app:celery_app worker --loglevel=INFO --pool=gevent --concurrency=100
```

## Monitoring

```bash
# Monitor tasks
celery -A src.services.celery_app:celery_app events

# Flower web interface (install with: pip install flower)
celery -A src.services.celery_app:celery_app flower
```