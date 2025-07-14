"""
OCR service for extracting text from images using PaddleOCR, EasyOCR, and Mistral AI.
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
    """Simplified EasyOCR implementation"""
    
    def __init__(self):
        self.reader = None
        self._initialize_reader()
    
    def _initialize_reader(self):
        """Initialize EasyOCR reader with simple configuration"""
        try:
            print("Initializing EasyOCR...")
            
            import easyocr
            
            # Parse languages from settings
            lang_list = settings.easy_ocr_lang_list
            
            # Simple initialization - let EasyOCR handle defaults
            self.reader = easyocr.Reader(
                lang_list=lang_list,
                gpu=settings.easy_ocr_use_gpu,
                model_storage_directory=settings.easy_ocr_model_storage,
                download_enabled=True,
                verbose=False
            )
            
            print(f"EasyOCR initialized successfully with languages: {lang_list}")
            
        except Exception as e:
            print(f"EasyOCR initialization failed: {str(e)}")
            raise ConversionException(f"Failed to initialize EasyOCR: {str(e)}")
    
    def extract_text(self, image: Image.Image) -> OCRResult:
        """Extract text using EasyOCR with simple approach"""
        try:
            import numpy as np
            
            # Convert PIL image to numpy array
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            image_array = np.array(image)
            
            # Simple OCR call - use defaults for most parameters
            results = self.reader.readtext(image_array)
            
            # Extract text from results
            extracted_text = []
            total_confidence = 0.0
            line_count = 0
            
            for (bbox, text, confidence) in results:
                text = str(text).strip()
                if text:  # Include all text regardless of confidence
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
                    'languages': settings.easy_ocr_lang_list,
                    'lines_detected': line_count
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
        """Initialize available OCR providers"""
        # Try to initialize each provider
        providers_to_try = [
            ('paddle', PaddleOCRProvider),
            ('easyocr', EasyOCRProvider),
            ('mistral', MistralOCRProvider)
        ]
        
        for provider_name, provider_class in providers_to_try:
            try:
                if provider_name == 'mistral' and not settings.mistral_api_key:
                    print(f"Skipping {provider_name}: API key not configured")
                    continue
                    
                print(f"Initializing {provider_name} provider...")
                self._providers[provider_name] = provider_class()
                print(f"{provider_name} provider initialized successfully")
                
            except Exception as e:
                print(f"Warning: {provider_name} OCR not available: {e}")
        
        if not self._providers:
            raise ConversionException("No OCR providers could be initialized")
        
        print(f"Available OCR providers: {list(self._providers.keys())}")
    
    def extract_text(self, image: Image.Image, provider: str = 'paddle') -> OCRResult:
        """Extract text from image using specified provider"""
        # Use the first available provider if requested one is not available
        if provider not in self._providers:
            available = list(self._providers.keys())
            if available:
                provider = available[0]
                print(f"Requested provider not available, using: {provider}")
            else:
                raise ConversionException("No OCR providers are available")
        
        try:
            return self._providers[provider].extract_text(image)
        except Exception as e:
            print(f"OCR extraction failed with {provider}: {e}")
            raise ConversionException(f"OCR extraction failed: {str(e)}")
    
    def get_available_providers(self) -> List[str]:
        """Get list of available OCR providers"""
        return list(self._providers.keys())


# Global OCR service instance
ocr_service = OCRService()