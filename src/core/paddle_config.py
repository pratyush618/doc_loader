"""
Simplified PaddlePaddle configuration
"""
import os
import warnings
from pathlib import Path

# Set up models directory
project_root = Path(__file__).parent.parent.parent
models_dir = project_root / "models" / "paddle_models"
models_dir.mkdir(parents=True, exist_ok=True)

# Set environment variables for PaddleOCR model storage
os.environ['PADDLEOCR_HOME'] = str(models_dir.resolve())
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'  # Force CPU mode
os.environ['GLOG_minloglevel'] = '2'      # Reduce logging

# Suppress warnings
warnings.filterwarnings('ignore')

def get_models_dir():
    """Get the models directory path"""
    return str(models_dir.resolve())

def suppress_paddle_logs():
    """Suppress PaddleOCR logging"""
    import logging
    logging.getLogger('paddle').setLevel(logging.ERROR)
    logging.getLogger('paddleocr').setLevel(logging.ERROR)
    logging.getLogger('ppocr').setLevel(logging.ERROR)

print(f"PaddleOCR models directory: {get_models_dir()}")