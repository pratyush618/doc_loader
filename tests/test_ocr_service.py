"""
Tests for OCR service
"""
import pytest
from PIL import Image
from unittest.mock import Mock, patch

from src.services.ocr_service import (
    OCRService, OCRResult, PaddleOCRProvider, 
    EasyOCRProvider, MistralOCRProvider
)
from src.core.exceptions import ConversionException


class TestOCRResult:
    """Test OCRResult class"""
    
    def test_ocr_result_creation(self):
        """Test creating an OCR result"""
        result = OCRResult(
            text="Extracted text",
            confidence=0.95,
            metadata={"provider": "paddle", "lines": 5}
        )
        
        assert result.text == "Extracted text"
        assert result.confidence == 0.95
        assert result.metadata["provider"] == "paddle"
        assert result.metadata["lines"] == 5
    
    def test_ocr_result_defaults(self):
        """Test OCR result with default values"""
        result = OCRResult(text="Test")
        
        assert result.text == "Test"
        assert result.confidence == 1.0
        assert result.metadata == {}


class TestPaddleOCRProvider:
    """Test PaddleOCR provider"""
    
    @patch('src.services.ocr_service.PaddleOCR')
    def test_paddle_initialization(self, mock_paddle_class):
        """Test PaddleOCR initialization"""
        mock_paddle_instance = Mock()
        mock_paddle_class.return_value = mock_paddle_instance
        
        provider = PaddleOCRProvider()
        
        assert provider.ocr is not None
        mock_paddle_class.assert_called_once_with(
            lang='ch',
            use_angle_cls=True
        )
    
    @patch('src.services.ocr_service.PaddleOCR')
    def test_paddle_extract_text(self, mock_paddle_class):
        """Test text extraction with PaddleOCR"""
        # Setup mock
        mock_ocr = Mock()
        mock_ocr.ocr.return_value = [[
            [[[0, 0], [100, 0], [100, 20], [0, 20]], ('Hello World', 0.98)],
            [[[0, 30], [100, 30], [100, 50], [0, 50]], ('Second line', 0.95)]
        ]]
        mock_paddle_class.return_value = mock_ocr
        
        provider = PaddleOCRProvider()
        
        # Create test image
        img = Image.new('RGB', (200, 100), color='white')
        
        result = provider.extract_text(img)
        
        assert isinstance(result, OCRResult)
        assert "Hello World" in result.text
        assert "Second line" in result.text
        assert result.confidence > 0.9
        assert result.metadata["provider"] == "paddle"
        assert result.metadata["lines_detected"] == 2
    
    @patch('src.services.ocr_service.PaddleOCR')
    def test_paddle_extract_text_empty(self, mock_paddle_class):
        """Test PaddleOCR with no text detected"""
        mock_ocr = Mock()
        mock_ocr.ocr.return_value = [[]]
        mock_paddle_class.return_value = mock_ocr
        
        provider = PaddleOCRProvider()
        img = Image.new('RGB', (100, 100), color='white')
        
        result = provider.extract_text(img)
        
        assert result.text == ""
        assert result.confidence == 0.0
        assert result.metadata["lines_detected"] == 0
    
    @patch('src.services.ocr_service.PaddleOCR')
    def test_paddle_extract_text_error(self, mock_paddle_class):
        """Test PaddleOCR error handling"""
        mock_ocr = Mock()
        mock_ocr.ocr.side_effect = Exception("OCR failed")
        mock_paddle_class.return_value = mock_ocr
        
        provider = PaddleOCRProvider()
        img = Image.new('RGB', (100, 100), color='white')
        
        with pytest.raises(ConversionException, match="PaddleOCR extraction failed"):
            provider.extract_text(img)


class TestEasyOCRProvider:
    """Test EasyOCR provider"""
    
    @patch('easyocr.Reader')
    def test_easyocr_initialization(self, mock_reader_class):
        """Test EasyOCR initialization"""
        mock_reader = Mock()
        mock_reader_class.return_value = mock_reader
        
        with patch('src.core.config.settings') as mock_settings:
            mock_settings.easy_ocr_lang_list = ['en']
            mock_settings.easy_ocr_use_gpu = False
            mock_settings.easy_ocr_model_storage = './models'
            
            provider = EasyOCRProvider()
            
            assert provider.reader is not None
            mock_reader_class.assert_called_once_with(
                lang_list=['en'],
                gpu=False,
                model_storage_directory='./models',
                download_enabled=True,
                verbose=False
            )
    
    @patch('easyocr.Reader')
    def test_easyocr_extract_text(self, mock_reader_class):
        """Test text extraction with EasyOCR"""
        mock_reader = Mock()
        mock_reader.readtext.return_value = [
            ([[0, 0], [100, 0], [100, 20], [0, 20]], 'Hello World', 0.98),
            ([[0, 30], [100, 30], [100, 50], [0, 50]], 'Test text', 0.95)
        ]
        mock_reader_class.return_value = mock_reader
        
        with patch('src.core.config.settings') as mock_settings:
            mock_settings.easy_ocr_lang_list = ['en']
            mock_settings.easy_ocr_use_gpu = False
            mock_settings.easy_ocr_model_storage = './models'
            
            provider = EasyOCRProvider()
            img = Image.new('RGB', (200, 100), color='white')
            
            result = provider.extract_text(img)
            
            assert isinstance(result, OCRResult)
            assert "Hello World" in result.text
            assert "Test text" in result.text
            assert result.confidence > 0.9
            assert result.metadata["provider"] == "easyocr"
            assert result.metadata["lines_detected"] == 2
    
    @patch('easyocr.Reader')
    def test_easyocr_extract_text_empty(self, mock_reader_class):
        """Test EasyOCR with no text detected"""
        mock_reader = Mock()
        mock_reader.readtext.return_value = []
        mock_reader_class.return_value = mock_reader
        
        with patch('src.core.config.settings') as mock_settings:
            mock_settings.easy_ocr_lang_list = ['en']
            mock_settings.easy_ocr_use_gpu = False
            mock_settings.easy_ocr_model_storage = './models'
            
            provider = EasyOCRProvider()
            img = Image.new('RGB', (100, 100), color='white')
            
            result = provider.extract_text(img)
            
            assert result.text == ""
            assert result.confidence == 0.0
            assert result.metadata["lines_detected"] == 0


class TestMistralOCRProvider:
    """Test Mistral OCR provider"""
    
    def test_mistral_initialization_no_api_key(self):
        """Test Mistral initialization without API key"""
        with patch('src.core.config.settings') as mock_settings:
            mock_settings.mistral_api_key = None
            
            with pytest.raises(ConversionException, match="Mistral API key not configured"):
                MistralOCRProvider()
    
    @patch('httpx.Client')
    def test_mistral_extract_text(self, mock_client_class):
        """Test text extraction with Mistral"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Extracted text from image"
                }
            }],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50
            }
        }
        
        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        with patch('src.core.config.settings') as mock_settings:
            mock_settings.mistral_api_key = "test-key"
            mock_settings.mistral_api_url = "https://api.mistral.ai/v1/chat/completions"
            mock_settings.mistral_model = "pixtral-12b"
            
            provider = MistralOCRProvider()
            img = Image.new('RGB', (100, 100), color='white')
            
            result = provider.extract_text(img)
            
            assert isinstance(result, OCRResult)
            assert result.text == "Extracted text from image"
            assert result.confidence == 1.0
            assert result.metadata["provider"] == "mistral"
            assert result.metadata["model"] == "pixtral-12b"
            assert "usage" in result.metadata
    
    @patch('httpx.Client')
    def test_mistral_extract_text_api_error(self, mock_client_class):
        """Test Mistral API error handling"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        with patch('src.core.config.settings') as mock_settings:
            mock_settings.mistral_api_key = "test-key"
            mock_settings.mistral_api_url = "https://api.mistral.ai/v1/chat/completions"
            mock_settings.mistral_model = "pixtral-12b"
            
            provider = MistralOCRProvider()
            img = Image.new('RGB', (100, 100), color='white')
            
            with pytest.raises(ConversionException, match="Mistral API error"):
                provider.extract_text(img)


class TestOCRService:
    """Test main OCR service"""
    
    @patch('src.services.ocr_service.PaddleOCRProvider')
    @patch('src.services.ocr_service.EasyOCRProvider')
    def test_service_initialization(self, mock_easy, mock_paddle):
        """Test OCR service initialization"""
        mock_paddle_instance = Mock()
        mock_easy_instance = Mock()
        mock_paddle.return_value = mock_paddle_instance
        mock_easy.return_value = mock_easy_instance
        
        with patch('src.core.config.settings') as mock_settings:
            mock_settings.mistral_api_key = None
            
            service = OCRService()
            
            assert len(service._providers) >= 1
            assert service.get_available_providers() == list(service._providers.keys())
    
    @patch('src.services.ocr_service.PaddleOCRProvider')
    def test_extract_text_with_provider(self, mock_paddle_class):
        """Test extracting text with specific provider"""
        mock_provider = Mock()
        mock_result = OCRResult("Test text", 0.95, {"provider": "paddle"})
        mock_provider.extract_text.return_value = mock_result
        mock_paddle_class.return_value = mock_provider
        
        with patch('src.core.config.settings') as mock_settings:
            mock_settings.mistral_api_key = None
            
            service = OCRService()
            img = Image.new('RGB', (100, 100), color='white')
            
            result = service.extract_text(img, provider='paddle')
            
            assert result.text == "Test text"
            assert result.confidence == 0.95
            mock_provider.extract_text.assert_called_once()
    
    @patch('src.services.ocr_service.PaddleOCRProvider')
    def test_extract_text_provider_not_available(self, mock_paddle_class):
        """Test fallback when requested provider is not available"""
        mock_provider = Mock()
        mock_result = OCRResult("Fallback text", 0.90, {"provider": "paddle"})
        mock_provider.extract_text.return_value = mock_result
        mock_paddle_class.return_value = mock_provider
        
        with patch('src.core.config.settings') as mock_settings:
            mock_settings.mistral_api_key = None
            
            service = OCRService()
            img = Image.new('RGB', (100, 100), color='white')
            
            # Request unavailable provider
            result = service.extract_text(img, provider='unavailable')
            
            # Should use available provider
            assert result.text == "Fallback text"
            mock_provider.extract_text.assert_called_once()
    
    def test_no_providers_available(self):
        """Test when no OCR providers can be initialized"""
        with patch('src.services.ocr_service.PaddleOCRProvider') as mock_paddle:
            with patch('src.services.ocr_service.EasyOCRProvider') as mock_easy:
                with patch('src.core.config.settings') as mock_settings:
                    mock_settings.mistral_api_key = None
                    mock_paddle.side_effect = Exception("Paddle failed")
                    mock_easy.side_effect = Exception("EasyOCR failed")
                    
                    with pytest.raises(ConversionException, match="No OCR providers could be initialized"):
                        OCRService()