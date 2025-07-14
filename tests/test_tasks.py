"""
Tests for Celery tasks
"""
import pytest
from unittest.mock import Mock, patch
import json

from src.services.tasks import (
    _convert_document_sync, _create_structured_json,
    _structure_pdf_content, _structure_presentation_content,
    _structure_spreadsheet_content, _structure_document_content
)
from src.models.job import Job, JobStatus, OutputFormat
from src.converters.base import ConverterResult
from src.core.exceptions import ConversionException


class TestConversionTask:
    """Test document conversion task"""
    
    @patch('src.services.tasks.sync_job_store')
    @patch('src.services.tasks.sync_storage')
    @patch('src.services.tasks.registry')
    @patch('src.services.tasks.sync_webhook_service')
    def test_convert_document_success(self, mock_webhook, mock_registry, mock_storage, mock_job_store):
        """Test successful document conversion"""
        # Setup mocks
        job = Job(
            id="test-123",
            file_name="test.txt",
            file_path="/uploads/test.txt",
            output_format=OutputFormat.MARKDOWN,
            status=JobStatus.PENDING,
            webhook_url="http://example.com/webhook"
        )
        
        mock_job_store.get.return_value = job
        mock_storage.read_file.return_value = b"Test content"
        mock_storage.save_result.return_value = "/outputs/test.md"
        mock_storage.get_result_url.return_value = "http://localhost/api/v1/jobs/test-123/result"
        
        # Mock converter
        mock_converter = Mock()
        mock_converter.convert = Mock(return_value=ConverterResult(
            content="# Converted Content\n\nTest content",
            title="test.txt",
            metadata={"pages": 1}
        ))
        mock_registry.get_converter.return_value = mock_converter
        
        # Create a mock task
        mock_task = Mock()
        mock_task.update_job_progress = Mock()
        
        # Run conversion
        result = _convert_document_sync(mock_task, "test-123")
        
        # Verify result
        assert result["job_id"] == "test-123"
        assert result["status"] == "completed"
        assert result["result_path"] == "/outputs/test.md"
        assert result["result_url"] == "http://localhost/api/v1/jobs/test-123/result"
        
        # Verify job updates
        assert mock_job_store.update.call_count >= 2  # At least start and completion
        final_update = mock_job_store.update.call_args_list[-1][0][1]
        assert final_update.status == JobStatus.COMPLETED
        assert final_update.progress == 100
        
        # Verify webhook was called
        mock_webhook.notify_job_status.assert_called()
    
    @patch('src.services.tasks.sync_job_store')
    @patch('src.services.tasks.sync_storage')
    @patch('src.services.tasks.registry')
    @patch('src.services.tasks.sync_webhook_service')
    def test_convert_document_json_output(self, mock_webhook, mock_registry, mock_storage, mock_job_store):
        """Test document conversion with JSON output"""
        # Setup job with JSON output
        job = Job(
            id="test-123",
            file_name="test.pdf",
            file_path="/uploads/test.pdf",
            output_format=OutputFormat.JSON,
            status=JobStatus.PENDING
        )
        
        mock_job_store.get.return_value = job
        mock_storage.read_file.return_value = b"PDF content"
        mock_storage.save_result.return_value = "/outputs/test.json"
        
        # Mock converter result
        mock_converter = Mock()
        mock_converter.convert = Mock(return_value=ConverterResult(
            content="## Page 1\n\nPage content here",
            title="test.pdf",
            metadata={"author": "Test Author"},
            images={"image1.png": b"image data"}
        ))
        mock_registry.get_converter.return_value = mock_converter
        
        mock_task = Mock()
        mock_task.update_job_progress = Mock()
        
        # Run conversion
        result = _convert_document_sync(mock_task, "test-123")  # noqa: F841
        
        # Verify JSON was saved
        saved_content = mock_storage.save_result.call_args[0][1]
        json_data = json.loads(saved_content)
        
        assert json_data["document"]["filename"] == "test.pdf"
        assert json_data["document"]["type"] == "PDF Document"
        assert "content" in json_data
        assert "images" in json_data
    
    @patch('src.services.tasks.sync_job_store')
    @patch('src.services.tasks.sync_storage')
    @patch('src.services.tasks.registry')
    def test_convert_document_failure(self, mock_registry, mock_storage, mock_job_store):
        """Test document conversion failure"""
        job = Job(
            id="test-123",
            file_name="test.txt",
            file_path="/uploads/test.txt",
            output_format=OutputFormat.MARKDOWN,
            status=JobStatus.PENDING
        )
        
        mock_job_store.get.return_value = job
        mock_storage.read_file.side_effect = Exception("File read error")
        
        mock_task = Mock()
        mock_task.update_job_progress = Mock()
        
        # Run conversion and expect exception
        with pytest.raises(ConversionException):
            _convert_document_sync(mock_task, "test-123")
        
        # Verify job was marked as failed
        update_calls = mock_job_store.update.call_args_list
        assert any(
            call[0][1].status == JobStatus.FAILED 
            for call in update_calls
        )


class TestStructuredJsonCreation:
    """Test structured JSON creation functions"""
    
    def test_create_structured_json_pdf(self):
        """Test creating structured JSON for PDF"""
        result = ConverterResult(
            content="## Page 1\n\nFirst page content\n\n## Page 2\n\nSecond page content",
            title="Document Title",
            metadata={"pages": 2, "author": "Test Author"}
        )
        
        json_output = _create_structured_json(result, "test.pdf")
        
        assert json_output["document"]["filename"] == "test.pdf"
        assert json_output["document"]["type"] == "PDF Document"
        assert json_output["document"]["metadata"]["pages"] == 2
        
        # Check content structure
        content = json_output["content"]
        assert content["type"] == "multi_page_document"
        assert content["total_pages"] == 2
        assert len(content["pages"]) == 2
        assert content["pages"][0]["page_number"] == 1
        assert "First page content" in content["pages"][0]["text"]
    
    def test_create_structured_json_presentation(self):
        """Test creating structured JSON for presentation"""
        result = ConverterResult(
            content="# Slide 1\n\n## Title Slide\n\nWelcome\n\n# Slide 2\n\n## Content\n\n- Point 1\n- Point 2",
            title="Presentation",
            metadata={"slides": 2}
        )
        
        json_output = _create_structured_json(result, "test.pptx")
        
        assert json_output["document"]["type"] == "PowerPoint Presentation"
        
        content = json_output["content"]
        assert content["type"] == "presentation"
        assert content["total_slides"] == 2
        assert len(content["slides"]) == 2
        assert content["slides"][0]["slide_number"] == 1
        assert "Title Slide" in content["slides"][0]["text"]
    
    def test_create_structured_json_spreadsheet(self):
        """Test creating structured JSON for spreadsheet"""
        result = ConverterResult(
            content="# Sheet: Sales\n\n| Product | Price | Quantity |\n|---------|-------|----------|\n| Widget A | 10.00 | 5 |\n| Widget B | 20.00 | 3 |\n\n# Sheet: Summary\n\n*Empty sheet*",
            title="Spreadsheet",
            metadata={"sheet_names": ["Sales", "Summary"]}
        )
        
        json_output = _create_structured_json(result, "test.xlsx")
        
        assert json_output["document"]["type"] == "Excel Workbook"
        
        content = json_output["content"]
        assert content["type"] == "spreadsheet"
        assert content["total_sheets"] == 2
        assert len(content["sheets"]) == 2
        
        # Check first sheet
        sales_sheet = content["sheets"][0]
        assert sales_sheet["sheet_name"] == "Sales"
        assert sales_sheet["headers"] == ["Product", "Price", "Quantity"]
        assert sales_sheet["has_data"] is True
        assert len(sales_sheet["sample_data"]) > 0
        
        # Check empty sheet
        summary_sheet = content["sheets"][1]
        assert summary_sheet["sheet_name"] == "Summary"
        assert summary_sheet["has_data"] is False
    
    def test_create_structured_json_document(self):
        """Test creating structured JSON for document"""
        result = ConverterResult(
            content="# Introduction\n\nThis is the intro.\n\n# Chapter 1\n\nChapter content here.\n\n# Conclusion\n\nFinal thoughts.",
            title="Document",
            metadata={"sections": 3}
        )
        
        json_output = _create_structured_json(result, "test.docx")
        
        assert json_output["document"]["type"] == "Word Document"
        
        content = json_output["content"]
        assert content["type"] == "structured_document"
        assert content["total_sections"] == 3
        assert len(content["sections"]) == 3
        
        assert content["sections"][0]["heading"] == "Introduction"
        assert "This is the intro" in content["sections"][0]["text"]
    
    def test_create_structured_json_with_images(self):
        """Test creating structured JSON with images"""
        result = ConverterResult(
            content="Content with images",
            title="Document",
            metadata={},
            images={
                "image1.png": b"image data 1",
                "image2.jpg": b"image data 2"
            }
        )
        
        json_output = _create_structured_json(result, "test.pdf")
        
        assert len(json_output["images"]) == 2
        assert "image1.png" in json_output["images"]
        assert "image2.jpg" in json_output["images"]
        # Images should be base64 encoded
        assert isinstance(json_output["images"]["image1.png"], str)


class TestContentStructuringFunctions:
    """Test individual content structuring functions"""
    
    def test_structure_pdf_content(self):
        """Test PDF content structuring"""
        content = "## Page 1\n\nFirst page\n\n## Page 2\n\nSecond page\n\n## Page 3\n\nThird page"
        
        result = _structure_pdf_content(content)
        
        assert result["type"] == "multi_page_document"
        assert result["total_pages"] == 3
        assert len(result["pages"]) == 3
        
        for i, page in enumerate(result["pages"]):
            assert page["page_number"] == i + 1
            assert page["word_count"] > 0
    
    def test_structure_presentation_content(self):
        """Test presentation content structuring"""
        content = "# Slide 1\n\n## Title\n\nContent\n\n# Slide 2\n\n## Another Slide\n\nMore content"
        
        result = _structure_presentation_content(content)
        
        assert result["type"] == "presentation"
        assert result["total_slides"] == 2
        assert len(result["slides"]) == 2
        
        assert result["slides"][0]["slide_number"] == 1
        assert "Title" in result["slides"][0]["summary"]
    
    def test_structure_spreadsheet_content(self):
        """Test spreadsheet content structuring"""
        content = """# Sheet: Data
        
| Col1 | Col2 | Col3 |
|------|------|------|
| A1   | B1   | C1   |
| A2   | B2   | C2   |

# Sheet: Empty

*Empty sheet*"""
        
        metadata = {"sheet_names": ["Data", "Empty"]}
        result = _structure_spreadsheet_content(content, metadata)
        
        assert result["type"] == "spreadsheet"
        assert result["total_sheets"] == 2
        
        # Check data sheet
        data_sheet = result["sheets"][0]
        assert data_sheet["sheet_name"] == "Data"
        assert data_sheet["headers"] == ["Col1", "Col2", "Col3"]
        assert data_sheet["has_data"] is True
        assert len(data_sheet["sample_data"]) > 0
        
        # Check empty sheet
        empty_sheet = result["sheets"][1]
        assert empty_sheet["sheet_name"] == "Empty"
        assert empty_sheet["has_data"] is False
    
    def test_structure_document_content(self):
        """Test document content structuring"""
        content = """# Executive Summary

This is the summary.

# Introduction

Introduction text here.

# Body

Main content of the document.

# Conclusion

Final thoughts."""
        
        result = _structure_document_content(content)
        
        assert result["type"] == "structured_document"
        assert result["total_sections"] == 4
        
        sections = result["sections"]
        assert sections[0]["heading"] == "Executive Summary"
        assert "This is the summary" in sections[0]["text"]
        assert sections[0]["word_count"] > 0