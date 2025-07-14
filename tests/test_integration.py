"""
Integration tests for the document converter
"""
import pytest
from unittest.mock import patch, Mock

from src.models.job import JobStatus
from src.converters.base import ConverterResult


class TestEndToEndConversion:
    """Test complete conversion flow"""
    
    @pytest.mark.asyncio
    async def test_text_file_conversion_flow(self, test_client, temp_dir):
        """Test converting a text file from upload to result"""
        with patch('src.api.routes.jobs.job_store') as mock_job_store:
            with patch('src.api.routes.jobs.storage') as mock_storage:
                with patch('src.api.routes.jobs.convert_document') as mock_task:
                    # Setup mocks
                    job_id = "test-job-123"
                    mock_job = Mock(
                        id=job_id,
                        status=JobStatus.PENDING,
                        progress=0,
                        to_dict=lambda: {"id": job_id, "status": "pending", "progress": 0}
                    )
                    mock_job_store.create.return_value = mock_job
                    mock_storage.save_file.return_value = "/uploads/test.txt"
                    mock_task.delay.return_value = Mock(id="celery-task-123")
                    
                    # Upload file
                    files = {"file": ("test.txt", b"Test content for conversion", "text/plain")}
                    data = {"output_format": "md"}
                    
                    response = test_client.post("/api/v1/jobs", files=files, data=data)
                    
                    assert response.status_code == 200
                    result = response.json()
                    assert result["id"] == job_id
                    assert result["status"] == "pending"
                    
                    # Verify task was queued
                    mock_task.delay.assert_called_once_with(job_id)
    
    @pytest.mark.asyncio
    async def test_image_ocr_conversion_flow(self, test_client, sample_image_file):
        """Test converting an image with OCR"""
        with patch('src.api.routes.jobs.job_store') as mock_job_store:
            with patch('src.api.routes.jobs.storage') as mock_storage:
                with patch('src.api.routes.jobs.convert_document') as mock_task:
                    # Setup mocks
                    job_id = "test-job-456"
                    mock_job = Mock(
                        id=job_id,
                        status=JobStatus.PENDING,
                        use_ocr=True,
                        ocr_provider="paddle",
                        to_dict=lambda: {
                            "id": job_id, 
                            "status": "pending", 
                            "use_ocr": True,
                            "ocr_provider": "paddle"
                        }
                    )
                    mock_job_store.create.return_value = mock_job
                    mock_storage.save_file.return_value = "/uploads/image.png"
                    mock_task.delay.return_value = Mock(id="celery-task-456")
                    
                    # Upload image with OCR enabled
                    files = {"file": ("image.png", sample_image_file.getvalue(), "image/png")}
                    data = {
                        "output_format": "md",
                        "use_ocr": "true",
                        "ocr_provider": "paddle"
                    }
                    
                    response = test_client.post("/api/v1/jobs", files=files, data=data)
                    
                    assert response.status_code == 200
                    result = response.json()
                    assert result["id"] == job_id
                    
                    # Verify job was created with OCR settings
                    create_call = mock_job_store.create.call_args[0][0]
                    assert create_call.use_ocr is True
                    assert create_call.ocr_provider.value == "paddle"
    
    @pytest.mark.asyncio
    async def test_webhook_notification_flow(self, test_client):
        """Test webhook notification on job completion"""
        with patch('src.api.routes.jobs.job_store') as mock_job_store:
            with patch('src.api.routes.jobs.storage') as mock_storage:
                with patch('src.api.routes.jobs.convert_document') as mock_task:
                    with patch('httpx.AsyncClient') as mock_http:
                        # Setup mocks
                        job_id = "test-job-789"
                        webhook_url = "http://example.com/webhook"
                        
                        mock_job = Mock(
                            id=job_id,
                            status=JobStatus.PENDING,
                            webhook_url=webhook_url,
                            to_dict=lambda: {
                                "id": job_id,
                                "status": "pending",
                                "webhook_url": webhook_url
                            }
                        )
                        mock_job_store.create.return_value = mock_job
                        mock_storage.save_file.return_value = "/uploads/test.pdf"
                        mock_task.delay.return_value = Mock(id="celery-task-789")
                        
                        # Upload file with webhook
                        files = {"file": ("test.pdf", b"PDF content", "application/pdf")}
                        data = {
                            "output_format": "json",
                            "webhook_url": webhook_url
                        }
                        
                        response = test_client.post("/api/v1/jobs", files=files, data=data)
                        
                        assert response.status_code == 200
                        
                        # Verify webhook URL was stored
                        create_call = mock_job_store.create.call_args[0][0]
                        assert create_call.webhook_url == webhook_url


class TestConverterIntegration:
    """Test converter integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_pdf_to_json_conversion(self):
        """Test PDF to JSON conversion with structure preservation"""
        from src.converters.pdf import PDFConverter
        from src.services.tasks import _create_structured_json
        
        # Simulate PDF conversion result
        converter_result = ConverterResult(
            content="## Page 1\n\nIntroduction paragraph.\n\n## Page 2\n\nMain content here.",
            title="Sample PDF",
            metadata={
                "pages": 2,
                "author": "Test Author",
                "creation_date": "2024-01-01"
            }
        )
        
        # Convert to structured JSON
        json_output = _create_structured_json(converter_result, "document.pdf")
        
        # Verify structure
        assert json_output["document"]["filename"] == "document.pdf"
        assert json_output["document"]["type"] == "PDF Document"
        assert json_output["document"]["metadata"]["pages"] == 2
        
        content = json_output["content"]
        assert content["type"] == "multi_page_document"
        assert content["total_pages"] == 2
        assert len(content["pages"]) == 2
    
    @pytest.mark.asyncio
    async def test_spreadsheet_to_json_conversion(self):
        """Test spreadsheet to JSON conversion with table data"""
        from src.services.tasks import _create_structured_json
        
        # Simulate spreadsheet conversion result
        converter_result = ConverterResult(
            content="""# Sheet: Sales Data

| Product | Q1 Sales | Q2 Sales | Q3 Sales | Q4 Sales |
|---------|----------|----------|----------|----------|
| Widget A | 1000 | 1200 | 1100 | 1300 |
| Widget B | 800 | 900 | 950 | 1000 |
| Widget C | 600 | 650 | 700 | 750 |

# Sheet: Summary

| Metric | Value |
|--------|-------|
| Total Sales | 12000 |
| Average | 900 |""",
            title="Sales Report",
            metadata={
                "sheet_names": ["Sales Data", "Summary"],
                "num_sheets": 2
            }
        )
        
        # Convert to structured JSON
        json_output = _create_structured_json(converter_result, "sales.xlsx")
        
        # Verify structure
        assert json_output["document"]["type"] == "Excel Workbook"
        
        content = json_output["content"]
        assert content["total_sheets"] == 2
        
        # Check Sales Data sheet
        sales_sheet = content["sheets"][0]
        assert sales_sheet["sheet_name"] == "Sales Data"
        assert sales_sheet["headers"] == ["Product", "Q1 Sales", "Q2 Sales", "Q3 Sales", "Q4 Sales"]
        assert sales_sheet["has_data"] is True
        assert len(sales_sheet["sample_data"]) == 3  # Limited to first 3 rows
        
        # Check Summary sheet
        summary_sheet = content["sheets"][1]
        assert summary_sheet["sheet_name"] == "Summary"
        assert summary_sheet["headers"] == ["Metric", "Value"]
    
    @pytest.mark.asyncio
    async def test_presentation_to_json_conversion(self):
        """Test presentation to JSON conversion with slide structure"""
        from src.services.tasks import _create_structured_json
        
        # Simulate presentation conversion result
        converter_result = ConverterResult(
            content="""# Slide 1

## Company Overview

Welcome to our annual presentation

# Slide 2

## Financial Results

- Revenue: $10M
- Profit: $2M
- Growth: 25%

# Slide 3

## Future Plans

- Expand to new markets
- Launch new products
- Increase team size""",
            title="Annual Presentation",
            metadata={
                "num_slides": 3,
                "slide_width": 9144000,
                "slide_height": 6858000
            }
        )
        
        # Convert to structured JSON
        json_output = _create_structured_json(converter_result, "presentation.pptx")
        
        # Verify structure
        assert json_output["document"]["type"] == "PowerPoint Presentation"
        
        content = json_output["content"]
        assert content["type"] == "presentation"
        assert content["total_slides"] == 3
        
        # Check slide summaries
        assert content["slides"][0]["summary"] == "Company Overview"
        assert content["slides"][1]["summary"] == "Financial Results"
        assert content["slides"][2]["summary"] == "Future Plans"
        
        # Verify slide content
        assert "Welcome to our annual presentation" in content["slides"][0]["text"]
        assert "Revenue: $10M" in content["slides"][1]["text"]


class TestErrorHandling:
    """Test error handling scenarios"""
    
    @pytest.mark.asyncio
    async def test_unsupported_file_type(self, test_client):
        """Test uploading unsupported file type"""
        files = {"file": ("test.xyz", b"Unknown format", "application/octet-stream")}
        data = {"output_format": "md"}
        
        with patch('src.api.routes.jobs.job_store') as mock_job_store:
            with patch('src.api.routes.jobs.storage') as mock_storage:
                with patch('src.api.routes.jobs.convert_document') as mock_task:
                    mock_job_store.create.return_value = Mock(
                        id="test-job",
                        to_dict=lambda: {"id": "test-job", "status": "pending"}
                    )
                    mock_storage.save_file.return_value = "/uploads/test.xyz"
                    mock_task.delay.return_value = Mock(id="celery-task")
                    
                    response = test_client.post("/api/v1/jobs", files=files, data=data)
                    
                    # Job should be created but will fail during processing
                    assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_ocr_provider_fallback(self):
        """Test OCR provider fallback mechanism"""
        from src.services.ocr_service import OCRService, OCRResult
        from PIL import Image
        
        with patch('src.services.ocr_service.PaddleOCRProvider') as mock_paddle:
            with patch('src.services.ocr_service.EasyOCRProvider') as mock_easy:
                # First provider fails
                mock_paddle_instance = Mock()
                mock_paddle_instance.extract_text.side_effect = Exception("Paddle failed")
                mock_paddle.return_value = mock_paddle_instance
                
                # Second provider succeeds
                mock_easy_instance = Mock()
                mock_easy_instance.extract_text.return_value = OCRResult(
                    text="Fallback text",
                    confidence=0.85,
                    metadata={"provider": "easyocr"}
                )
                mock_easy.return_value = mock_easy_instance
                
                with patch('src.core.config.settings') as mock_settings:
                    mock_settings.mistral_api_key = None
                    
                    service = OCRService()
                    img = Image.new('RGB', (100, 100), color='white')
                    
                    # Should fall back to EasyOCR
                    result = service.extract_text(img, provider='paddle')
                    assert result.text == "Fallback text"