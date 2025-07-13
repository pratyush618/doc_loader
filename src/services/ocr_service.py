"""
OCR service for extracting text from images using PaddleOCR and Mistral AI.
"""
import io
import base64
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from PIL import Image
import httpx

from ..core.config import settings
from ..core.exceptions import ConversionException
from ..core.paddle_config import suppress_paddle_logs

# Suppress logging before imports
suppress_paddle_logs()

class OCRResult:
    """OCR extraction result"""
    
    def __init__(self, text: str, confidence: float = 1.0, metadata: Optional[Dict[str, Any]] = None):
        self.text = text
        self.confidence = confidence
        self.metadata = metadata or {}


class BaseOCRProvider(ABC):
    """Base class for OCR providers"""
    
    @abstractmethod
    def extract_text(self, image: Image.Image) -> OCRResult:
        """Extract text from image"""
        pass


class PaddleOCRProvider(BaseOCRProvider):
    """Simplified PaddleOCR implementation"""
    
    def __init__(self):
        self.ocr = None
        self._initialize_ocr()
    
    def _initialize_ocr(self):
        """Initialize PaddleOCR with simple configuration"""
        try:
            print("Initializing PaddleOCR...")
            
            from paddleocr import PaddleOCR #type: ignore
            
            # Simple initialization with minimal parameters
            self.ocr = PaddleOCR(
                lang='ch',
                use_angle_cls=True
            )
            
            print("PaddleOCR initialized successfully")
            
        except Exception as e:
            print(f"PaddleOCR initialization failed: {str(e)}")
            raise ConversionException(f"Failed to initialize PaddleOCR: {str(e)}")
    
    def extract_text(self, image: Image.Image) -> OCRResult:
        """Extract text using PaddleOCR"""
        try:
            import numpy as np
            
            # Convert PIL image to numpy array
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            image_array = np.array(image)
            
            # Perform OCR
            result = self.ocr.ocr(image_array, cls=True)
            
            # Extract text from result
            extracted_text = []
            total_confidence = 0.0
            line_count = 0
            
            if result and result[0]:
                for line in result[0]:
                    if line and len(line) >= 2:
                        text_info = line[1]
                        if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                            text = str(text_info[0]).strip()
                            confidence = float(text_info[1])
                            
                            if confidence > 0.5 and text:
                                extracted_text.append(text)
                                total_confidence += confidence
                                line_count += 1
            
            # Calculate average confidence
            avg_confidence = total_confidence / line_count if line_count > 0 else 0.0
            full_text = '\n'.join(extracted_text)
            
            return OCRResult(
                text=full_text,
                confidence=avg_confidence,
                metadata={
                    'provider': 'paddle',
                    'language': 'ch',
                    'lines_detected': line_count
                }
            )
            
        except Exception as e:
            print(f"PaddleOCR extraction failed: {str(e)}")
            raise ConversionException(f"PaddleOCR extraction failed: {str(e)}")


class MistralOCRProvider(BaseOCRProvider):
    """Mistral AI OCR implementation"""
    
    def __init__(self):
        if not settings.mistral_api_key:
            raise ConversionException("Mistral API key not configured")
        
        self.api_key = settings.mistral_api_key
        self.api_url = settings.mistral_api_url
        self.model = settings.mistral_model
    
    def extract_text(self, image: Image.Image) -> OCRResult:
        """Extract text using Mistral AI vision model"""
        try:
            # Convert image to base64
            image_b64 = self._image_to_base64(image)
            
            # Prepare the request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract all text from this image. Return only the extracted text, preserving the original formatting and structure as much as possible. If there is no text in the image, return 'NO_TEXT_FOUND'."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_b64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 4000,
                "temperature": 0.0
            }
            
            # Make the API call
            with httpx.Client(timeout=60.0) as client:
                response = client.post(self.api_url, json=payload, headers=headers)
                
                if response.status_code != 200:
                    raise ConversionException(f"Mistral API error: {response.status_code} - {response.text}")
                
                result = response.json()
                
                # Extract text from response
                text = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
                
                if text == 'NO_TEXT_FOUND':
                    text = ''
                
                return OCRResult(
                    text=text,
                    confidence=1.0,
                    metadata={
                        'provider': 'mistral',
                        'model': self.model,
                        'usage': result.get('usage', {})
                    }
                )
                
        except Exception as e:
            raise ConversionException(f"Mistral OCR extraction failed: {str(e)}")
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL image to base64 string"""
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=95)
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode('utf-8')


class EasyOCRProvider(BaseOCRProvider):
    """EasyOCR implementation"""
    
    def __init__(self):
        self.reader = None
        self._initialize_reader()
    
    def _initialize_reader(self):
        """Initialize EasyOCR reader with Windows compatibility"""
        try:
            print("Initializing EasyOCR...")
            
            import os
            import platform
            
            # Windows-specific fixes
            if platform.system() == "Windows":
                # Set environment variables to help with DLL loading on Windows
                os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
                os.environ['OMP_NUM_THREADS'] = '1'
                
                # Try to fix torch DLL issues
                try:
                    import torch
                    # Force CPU mode on Windows to avoid GPU-related DLL issues
                    torch.set_num_threads(1)
                except Exception as torch_error:
                    print(f"Warning: Could not configure torch: {torch_error}")
            
            import easyocr
            
            # Set model storage directory
            os.environ['EASYOCR_MODULE_PATH'] = settings.easy_ocr_model_storage
            
            # Parse languages
            if hasattr(settings, 'easy_ocr_lang_list'):
                lang_list = settings.easy_ocr_lang_list
            else:
                lang_list = settings.easy_ocr_lang
            
            # Force CPU mode on Windows and when GPU is disabled
            use_gpu = settings.easy_ocr_use_gpu and platform.system() != "Windows"
            
            # Initialize EasyOCR reader with conservative settings
            self.reader = easyocr.Reader(
                lang_list=lang_list,
                gpu=use_gpu,
                model_storage_directory=settings.easy_ocr_model_storage,
                download_enabled=True,
                verbose=False
            )
            
            print(f"EasyOCR initialized successfully with languages: {lang_list}, GPU: {use_gpu}")
            
        except ImportError as e:
            if "torch" in str(e).lower() or "shm.dll" in str(e):
                print(f"EasyOCR initialization failed due to PyTorch/DLL issues: {str(e)}")
                print("This is common on Windows. Consider using PaddleOCR or Mistral OCR instead.")
                raise ConversionException(f"EasyOCR not available due to PyTorch compatibility issues: {str(e)}")
            else:
                raise ConversionException(f"Failed to initialize EasyOCR: {str(e)}")
        except Exception as e:
            print(f"EasyOCR initialization failed: {str(e)}")
            raise ConversionException(f"Failed to initialize EasyOCR: {str(e)}")
    
    def extract_text(self, image: Image.Image) -> OCRResult:
        """Extract text using EasyOCR"""
        try:
            import numpy as np
            
            # Convert PIL image to numpy array
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            image_array = np.array(image)
            
            # Perform OCR with EasyOCR
            results = self.reader.readtext(
                image_array,
                detail=1,  # Return bounding boxes and confidence
                paragraph=False,
                text_threshold=settings.easy_ocr_text_threshold,
                link_threshold=settings.easy_ocr_link_threshold,
                low_text=settings.easy_ocr_low_text
            )
            
            # Extract text and confidence
            extracted_text = []
            total_confidence = 0.0
            line_count = 0
            
            for result in results:
                if len(result) >= 3:
                    bbox, text, confidence = result
                    text = str(text).strip()
                    
                    if confidence > 0.5 and text:
                        extracted_text.append(text)
                        total_confidence += confidence
                        line_count += 1
            
            # Calculate average confidence
            avg_confidence = total_confidence / line_count if line_count > 0 else 0.0
            full_text = '\n'.join(extracted_text)
            
            return OCRResult(
                text=full_text,
                confidence=avg_confidence,
                metadata={
                    'provider': 'easyocr',
                    'languages': settings.easy_ocr_lang,
                    'lines_detected': line_count,
                    'text_threshold': settings.easy_ocr_text_threshold,
                    'link_threshold': settings.easy_ocr_link_threshold,
                    'low_text': settings.easy_ocr_low_text
                }
            )
            
        except Exception as e:
            print(f"EasyOCR extraction failed: {str(e)}")
            raise ConversionException(f"EasyOCR extraction failed: {str(e)}")


class OCRService:
    """Main OCR service that manages different providers"""
    
    def __init__(self):
        self._providers = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize available OCR providers with cross-platform support"""
        import platform
        system = platform.system()
        
        # Provider initialization order based on platform reliability
        provider_order = self._get_provider_order(system)
        
        for provider_name in provider_order:
            try:
                if provider_name == 'paddle':
                    print("Initializing PaddleOCR provider...")
                    self._providers['paddle'] = PaddleOCRProvider()
                    print("PaddleOCR provider initialized successfully")
                    
                elif provider_name == 'mistral':
                    if settings.mistral_api_key:
                        print("Initializing Mistral OCR provider...")
                        self._providers['mistral'] = MistralOCRProvider()
                        print("Mistral OCR provider initialized successfully")
                    else:
                        print("Skipping Mistral OCR: API key not configured")
                        
                elif provider_name == 'easyocr':
                    print("Initializing EasyOCR provider...")
                    self._providers['easyocr'] = EasyOCRProvider()
                    print("EasyOCR provider initialized successfully")
                    
            except Exception as e:
                print(f"Warning: {provider_name} OCR not available: {e}")
                # Continue with other providers
        
        # Ensure we have at least one working provider
        if not self._providers:
            raise ConversionException("No OCR providers could be initialized. Please check your environment.")
        
        print(f"Available OCR providers: {list(self._providers.keys())}")
    
    def _get_provider_order(self, system: str) -> list:
        """Get provider initialization order based on platform"""
        if system == "Windows":
            # On Windows, prioritize PaddleOCR and Mistral due to EasyOCR torch issues
            return ['paddle', 'mistral', 'easyocr']
        elif system == "Linux":
            # On Linux, all providers should work well
            return ['paddle', 'easyocr', 'mistral']
        elif system == "Darwin":  # macOS
            # On macOS, similar to Linux
            return ['paddle', 'easyocr', 'mistral']
        else:
            # Default order
            return ['paddle', 'mistral', 'easyocr']
    
    def extract_text(self, image: Image.Image, provider: str = 'paddle') -> OCRResult:
        """Extract text from image using specified provider with fallback"""
        # Try the requested provider first
        if provider in self._providers:
            try:
                result = self._providers[provider].extract_text(image)
                return result
            except Exception as e:
                print(f"Warning: {provider} OCR failed: {e}")
                # Continue to fallback
        
        # If requested provider failed or not available, try fallbacks
        available_providers = list(self._providers.keys())
        
        if not available_providers:
            raise ConversionException("No OCR providers are available")
        
        # Try each available provider as fallback
        for fallback_provider in available_providers:
            if fallback_provider == provider:
                continue  # Already tried
            
            try:
                print(f"Trying fallback OCR provider: {fallback_provider}")
                result = self._providers[fallback_provider].extract_text(image)
                result.metadata['fallback_used'] = True
                result.metadata['requested_provider'] = provider
                result.metadata['actual_provider'] = fallback_provider
                return result
            except Exception as e:
                print(f"Warning: Fallback provider {fallback_provider} also failed: {e}")
                continue
        
        # If all providers failed
        raise ConversionException(f"All OCR providers failed. Requested: {provider}, Available: {available_providers}")
    
    def get_best_provider(self) -> str:
        """Get the best available OCR provider for the current platform"""
        import platform
        system = platform.system()
        
        # Return the first available provider from the preferred order
        preferred_order = self._get_provider_order(system)
        for provider in preferred_order:
            if provider in self._providers:
                return provider
        
        # Fallback to any available provider
        if self._providers:
            return list(self._providers.keys())[0]
        
        raise ConversionException("No OCR providers available")
    
    def is_provider_available(self, provider: str) -> bool:
        """Check if an OCR provider is available"""
        return provider in self._providers
    
    def get_available_providers(self) -> List[str]:
        """Get list of available OCR providers"""
        return list(self._providers.keys())


# Global OCR service instance
ocr_service = OCRService()