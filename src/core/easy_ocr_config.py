"""
EasyOCR configuration utilities with cross-platform support
"""
import os
import platform
from pathlib import Path
from typing import List, Optional
from .config import settings

def get_platform_info():
    """Get platform information"""
    return {
        'system': platform.system(),
        'machine': platform.machine(),
        'is_windows': platform.system() == 'Windows',
        'is_linux': platform.system() == 'Linux',
        'is_mac': platform.system() == 'Darwin'
    }

def configure_easy_ocr_environment():
    """Configure EasyOCR environment variables with platform-specific settings"""
    # Set model storage directory
    model_dir = Path(settings.easy_ocr_model_storage)
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # Set environment variables
    os.environ['EASYOCR_MODULE_PATH'] = str(model_dir.resolve())
    
    # Platform-specific configurations
    platform_info = get_platform_info()
    
    if platform_info['is_windows']:
        # Windows-specific environment variables
        os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
        os.environ['OMP_NUM_THREADS'] = '1'
        os.environ['MKL_NUM_THREADS'] = '1'
        os.environ['TORCH_HOME'] = str(model_dir / 'torch')
        
    elif platform_info['is_linux']:
        # Linux-specific environment variables
        os.environ['OMP_NUM_THREADS'] = '4'
        os.environ['MKL_NUM_THREADS'] = '4'
        
    print(f"Platform: {platform_info['system']}")
    print(f"EasyOCR models directory: {model_dir.resolve()}")
    
    return str(model_dir.resolve())

def get_supported_languages():
    """Get list of supported languages"""
    # Common EasyOCR supported languages
    return [
        'en', 'ch_sim', 'ch_tra', 'fr', 'de', 'ja', 'ko', 
        'th', 'vi', 'ar', 'hi', 'es', 'pt', 'ru', 'it'
    ]

def download_models_if_needed(lang_list: List[str], model_dir: Path) -> bool:
    """Pre-download models if they don't exist"""
    try:
        import easyocr
        
        # Check if models exist
        models_exist = True
        for lang in lang_list:
            lang_dir = model_dir / lang
            if not lang_dir.exists() or not any(lang_dir.iterdir()):
                models_exist = False
                break
        
        if not models_exist:
            print(f"Pre-downloading EasyOCR models for languages: {lang_list}")
            
            # Create a temporary reader to download models
            temp_reader = easyocr.Reader(
                lang_list=lang_list,
                gpu=False,  # Use CPU for model download
                model_storage_directory=str(model_dir),
                download_enabled=True
            )
            
            # Clean up
            del temp_reader
            print("Models downloaded successfully")
            
        return True
        
    except Exception as e:
        print(f"Failed to download models: {e}")
        return False

def validate_easyocr_installation() -> tuple[bool, Optional[str]]:
    """Validate EasyOCR installation and dependencies"""
    try:
        # Test basic imports
        import torch
        import numpy as np
        
        # Test torch functionality
        torch.tensor([1, 2, 3])
        
        # Check if CUDA is available (but don't require it)
        cuda_available = torch.cuda.is_available()
        
        return True, f"EasyOCR validation passed (CUDA: {cuda_available})"
        
    except ImportError as e:
        return False, f"Missing dependency: {e}"
    except Exception as e:
        return False, f"Validation failed: {e}" 