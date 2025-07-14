"""
Simplified EasyOCR configuration utilities
"""
import os
from pathlib import Path
from .config import settings

def configure_easy_ocr_environment():
    """Configure EasyOCR environment with minimal setup"""
    # Create model storage directory
    model_dir = Path(settings.easy_ocr_model_storage)
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # Set model path environment variable
    os.environ['EASYOCR_MODULE_PATH'] = str(model_dir.resolve())
    
    print(f"EasyOCR models directory: {model_dir.resolve()}")
    
    return str(model_dir.resolve())

def get_supported_languages():
    """Get list of commonly supported languages"""
    return ['en', 'ch_sim', 'fr', 'de', 'ja', 'ko', 'es', 'ru']