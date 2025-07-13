#!/usr/bin/env python3
"""
Simple OCR test without loading full config
"""
import os
import sys
from pathlib import Path
from PIL import Image

# Set minimal required environment variables
os.environ['REDIS_URL'] = 'redis://localhost:6379/0'
os.environ['ALLOWED_ORIGINS'] = '*'
os.environ['SECRET_KEY'] = 'test-key'

# Import OCR service components directly
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Try importing PaddleOCR directly first
try:
    from services.ocr_service import PaddleOCRProvider, MistralOCRProvider, OCRService
    print("✅ OCR service imports successful")
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_simple_ocr():
    """Simple OCR test"""
    image_path = Path("D:/Text ti handwriting result.webp")
    
    if not image_path.exists():
        print(f"❌ Image not found: {image_path}")
        return
    
    print(f"🔍 Testing OCR on: {image_path}")
    print("=" * 50)
    
    # Load image
    try:
        image = Image.open(image_path)
        print(f"✅ Image loaded: {image.size}, format: {image.format}")
        
        if image.format == 'WEBP':
            print("✅ WebP format supported")
    except Exception as e:
        print(f"❌ Failed to load image: {e}")
        return
    
    # Test PaddleOCR directly
    print("\n🤖 Testing PaddleOCR:")
    try:
        paddle_ocr = PaddleOCRProvider()
        result = paddle_ocr.extract_text(image)
        
        print(f"📝 Text length: {len(result.text)} characters")
        print(f"🎯 Confidence: {result.confidence:.2f}")
        
        if result.text.strip():
            preview = result.text[:200] + "..." if len(result.text) > 200 else result.text
            print(f"📄 Text preview: '{preview}'")
        else:
            print("❌ No text extracted")
            
    except Exception as e:
        print(f"❌ PaddleOCR error: {e}")
    
    print("\n💡 For handwritten text, consider using Mistral AI OCR")
    print("   Add MISTRAL_API_KEY to environment for better results")

if __name__ == "__main__":
    test_simple_ocr()