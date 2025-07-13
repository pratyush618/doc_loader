#!/usr/bin/env python
import subprocess
import sys
import os

if __name__ == "__main__":
    # Set environment variable for Celery app
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.join(os.path.dirname(__file__), 'src')
    
    # Run Celery worker using command line
    cmd = [
        sys.executable, '-m', 'celery',
        '-A', 'src.services.celery_app:celery_app',
        'worker',
        '--loglevel=INFO',
        '--pool=solo',  # Windows compatible
        '--concurrency=1',
    ]
    
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, env=env)