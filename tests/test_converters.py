"""
Tests for document converters
"""
import pytest
import io
from PIL import Image
from unittest.mock import Mock, patch

from src.converters.base import ConverterResult
from src.converters.text import TextConverter
from src.converters.image import ImageConverter
from src.converters.pdf import PDFConverter
from src.converters.docx import DocxConverter
from src.converters.pptx import PPTXConverter
from src.converters.xlsx import XLSXConverter
from src.converters.rtf import RTFConverter
from src.converters.registry import ConverterRegistry
from src.core.exceptions import ConversionException


class TestTextConverter:
    """Test text file converter"""
    
    @pytest.mark.asyncio
    async def test_accepts_text_files(self):
        """Test that TextConverter accepts text files"""
        converter = TextConverter()
        
        # Test with .txt extension
        assert converter.accepts(io.BytesIO(b"text"), extension=".txt") is True
        assert converter.accepts(io.BytesIO(b"text"), extension=".md") is True
        assert converter.accepts(io.BytesIO(b"text"), extension=".log") is True
        
        # Test with MIME type
        assert converter.accepts(io.BytesIO(b"text"), mimetype="text/plain") is True
        
        # Test rejection of non-text files
        assert converter.accepts(io.BytesIO(b"text"), extension=".pdf") is False
        assert converter.accepts(io.BytesIO(b"text"), mimetype="image/png") is False
    
    @pytest.mark.asyncio
    async def test_convert_text_file(self):
        """Test converting a text file"""
        converter = TextConverter()
        content = "Hello, World!\nThis is a test file.\n"
        file = io.BytesIO(content.encode('utf-8'))
        
        result = await converter.convert(file, filename="test.txt")
        
        assert isinstance(result, ConverterResult)
        assert result.content == content
        assert result.title == "test.txt"
        assert result.metadata["format"] == "text"
        assert result.metadata["encoding"] == "utf-8"
    
    @pytest.mark.asyncio
    async def test_convert_text_with_different_encodings(self):
        """Test converting text files with different encodings"""
        converter = TextConverter()
        
        # Test UTF-8 with BOM
        content = "UTF-8 with BOM content"
        file = io.BytesIO(b'\xef\xbb\xbf' + content.encode('utf-8'))
        result = await converter.convert(file)
        assert result.content == content
        
        # Test Latin-1
        content = "Latin-1 content: café"
        file = io.BytesIO(content.encode('latin-1'))
        result = await converter.convert(file)
        assert "caf" in result.content  # May not decode special chars perfectly


class TestImageConverter:
    """Test image file converter"""
    
    @pytest.mark.asyncio
    async def test_accepts_image_files(self):
        """Test that ImageConverter accepts image files"""
        converter = ImageConverter()
        
        # Test with extensions
        for ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']:
            assert converter.accepts(io.BytesIO(b"img"), extension=ext) is True
        
        # Test with MIME types
        for mime in ['image/png', 'image/jpeg', 'image/gif']:
            assert converter.accepts(io.BytesIO(b"img"), mimetype=mime) is True
        
        # Test rejection of non-image files
        assert converter.accepts(io.BytesIO(b"text"), extension=".txt") is False
    
    @pytest.mark.asyncio
    async def test_convert_image_without_ocr(self, sample_image_file):
        """Test converting an image without OCR"""
        converter = ImageConverter()
        
        result = await converter.convert(sample_image_file, filename="test.png", use_ocr=False)
        
        assert isinstance(result, ConverterResult)
        assert result.title == "test.png"
        assert "test.png" in result.content
        assert len(result.images) == 1
        assert "test.png" in result.images
    
    @pytest.mark.asyncio
    async def test_convert_image_with_ocr(self, sample_image_file, mock_ocr_service):
        """Test converting an image with OCR"""
        converter = ImageConverter()
        
        # Configure mock OCR response
        mock_ocr_service.extract_text.return_value = Mock(
            text="Extracted text from image",
            confidence=0.95,
            metadata={"provider": "paddle"}
        )
        
        result = await converter.convert(
            sample_image_file, 
            filename="test.png", 
            use_ocr=True,
            ocr_provider="paddle"
        )
        
        assert isinstance(result, ConverterResult)
        assert "Extracted text from image" in result.content
        assert result.metadata["ocr_applied"] is True
        assert result.metadata["ocr_confidence"] == 0.95
        mock_ocr_service.extract_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_image_compression(self):
        """Test image compression during conversion"""
        converter = ImageConverter()
        
        # Create a large image
        img = Image.new('RGB', (3000, 3000), color='blue')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        result = await converter.convert(buffer, filename="large.png", use_ocr=False)
        
        # Check that image was compressed
        compressed_image = result.images.get("large.png")
        assert compressed_image is not None
        assert len(compressed_image) < buffer.getvalue().__len__()


class TestPDFConverter:
    """Test PDF file converter"""
    
    @pytest.mark.asyncio
    async def test_accepts_pdf_files(self):
        """Test that PDFConverter accepts PDF files"""
        converter = PDFConverter()
        
        assert converter.accepts(io.BytesIO(b"%PDF"), extension=".pdf") is True
        assert converter.accepts(io.BytesIO(b"%PDF"), mimetype="application/pdf") is True
        assert converter.accepts(io.BytesIO(b"text"), extension=".txt") is False
    
    @pytest.mark.asyncio
    async def test_convert_pdf_basic(self):
        """Test basic PDF conversion"""
        converter = PDFConverter()
        
        # Create a minimal PDF content
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        
        with patch('pypdf.PdfReader') as mock_pdf:
            # Mock PDF reader
            mock_reader = Mock()
            mock_reader.pages = [Mock(extract_text=Mock(return_value="Page 1 content"))]
            mock_reader.metadata = {}
            mock_pdf.return_value = mock_reader
            
            result = await converter.convert(io.BytesIO(pdf_content), filename="test.pdf")
            
            assert isinstance(result, ConverterResult)
            assert "Page 1 content" in result.content
            assert result.title == "test.pdf"


class TestDocxConverter:
    """Test DOCX file converter"""
    
    @pytest.mark.asyncio
    async def test_accepts_docx_files(self):
        """Test that DocxConverter accepts DOCX files"""
        converter = DocxConverter()
        
        assert converter.accepts(io.BytesIO(b"PK"), extension=".docx") is True
        assert converter.accepts(io.BytesIO(b"PK"), mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document") is True
        assert converter.accepts(io.BytesIO(b"text"), extension=".txt") is False
    
    @pytest.mark.asyncio
    async def test_convert_docx_basic(self):
        """Test basic DOCX conversion"""
        converter = DocxConverter()
        
        with patch('python_docx.Document') as mock_doc:
            # Mock document
            mock_document = Mock()
            mock_paragraph = Mock()
            mock_paragraph.text = "Test paragraph"
            mock_paragraph.style.name = "Normal"
            mock_document.paragraphs = [mock_paragraph]
            mock_document.tables = []
            mock_document.sections = []
            mock_doc.return_value = mock_document
            
            result = await converter.convert(io.BytesIO(b"fake docx"), filename="test.docx")
            
            assert isinstance(result, ConverterResult)
            assert "Test paragraph" in result.content
            assert result.title == "test.docx"


class TestPPTXConverter:
    """Test PPTX file converter"""
    
    @pytest.mark.asyncio
    async def test_accepts_pptx_files(self):
        """Test that PPTXConverter accepts PPTX files"""
        converter = PPTXConverter()
        
        assert converter.accepts(io.BytesIO(b"PK"), extension=".pptx") is True
        assert converter.accepts(io.BytesIO(b"PK"), extension=".pptm") is True
        assert converter.accepts(io.BytesIO(b"text"), extension=".txt") is False
    
    @pytest.mark.asyncio
    async def test_convert_pptx_basic(self):
        """Test basic PPTX conversion"""
        converter = PPTXConverter()
        
        with patch('python_pptx.Presentation') as mock_pres:
            # Mock presentation
            mock_presentation = Mock()
            mock_slide = Mock()
            mock_shape = Mock()
            mock_shape.has_text_frame = True
            mock_shape.text = "Slide content"
            mock_slide.shapes = [mock_shape]
            mock_presentation.slides = [mock_slide]
            mock_pres.return_value = mock_presentation
            
            result = await converter.convert(io.BytesIO(b"fake pptx"), filename="test.pptx")
            
            assert isinstance(result, ConverterResult)
            assert "Slide content" in result.content
            assert result.title == "test.pptx"


class TestXLSXConverter:
    """Test XLSX file converter"""
    
    @pytest.mark.asyncio
    async def test_accepts_xlsx_files(self):
        """Test that XLSXConverter accepts XLSX files"""
        converter = XLSXConverter()
        
        assert converter.accepts(io.BytesIO(b"PK"), extension=".xlsx") is True
        assert converter.accepts(io.BytesIO(b"PK"), extension=".xlsm") is True
        assert converter.accepts(io.BytesIO(b"text"), extension=".txt") is False
    
    @pytest.mark.asyncio
    async def test_convert_xlsx_basic(self):
        """Test basic XLSX conversion"""
        converter = XLSXConverter()
        
        with patch('openpyxl.load_workbook') as mock_load:
            # Mock workbook
            mock_workbook = Mock()
            mock_sheet = Mock()
            mock_sheet.title = "Sheet1"
            mock_sheet.max_row = 2
            mock_sheet.max_column = 2
            mock_sheet.cell = Mock(side_effect=lambda r, c: Mock(value=f"Cell{r}{c}"))
            mock_workbook.sheetnames = ["Sheet1"]
            mock_workbook.__getitem__ = Mock(return_value=mock_sheet)
            mock_load.return_value = mock_workbook
            
            result = await converter.convert(io.BytesIO(b"fake xlsx"), filename="test.xlsx")
            
            assert isinstance(result, ConverterResult)
            assert "Sheet1" in result.content
            assert result.title == "test.xlsx"


class TestRTFConverter:
    """Test RTF file converter"""
    
    @pytest.mark.asyncio
    async def test_accepts_rtf_files(self):
        """Test that RTFConverter accepts RTF files"""
        converter = RTFConverter()
        
        assert converter.accepts(io.BytesIO(b"{\\rtf"), extension=".rtf") is True
        assert converter.accepts(io.BytesIO(b"{\\rtf"), mimetype="application/rtf") is True
        assert converter.accepts(io.BytesIO(b"text"), extension=".txt") is False
    
    @pytest.mark.asyncio
    async def test_convert_rtf_basic(self):
        """Test basic RTF conversion"""
        converter = RTFConverter()
        
        rtf_content = b"{\\rtf1 Hello World}"
        result = await converter.convert(io.BytesIO(rtf_content), filename="test.rtf")
        
        assert isinstance(result, ConverterResult)
        assert "Hello World" in result.content
        assert result.title == "test.rtf"


class TestConverterRegistry:
    """Test converter registry"""
    
    def test_register_and_get_converter(self):
        """Test registering and retrieving converters"""
        registry = ConverterRegistry()
        
        # Register converters
        registry.register(TextConverter)
        registry.register(ImageConverter)
        
        # Test getting correct converter
        text_file = io.BytesIO(b"text content")
        converter = registry.get_converter(text_file, filename="test.txt")
        assert isinstance(converter, TextConverter)
        
        # Test with image file
        img_file = io.BytesIO(b"image")
        converter = registry.get_converter(img_file, filename="test.png")
        assert isinstance(converter, ImageConverter)
    
    def test_no_suitable_converter(self):
        """Test when no suitable converter is found"""
        registry = ConverterRegistry()
        registry.register(TextConverter)
        
        # Try with unsupported file type
        file = io.BytesIO(b"unknown")
        with pytest.raises(ConversionException, match="No suitable converter found"):
            registry.get_converter(file, filename="test.xyz")