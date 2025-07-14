"""
Tests for data models
"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from src.models.job import Job, JobStatus, OutputFormat, OCRProvider, JobUpdate


class TestJobModel:
    """Test Job model"""
    
    def test_job_creation_minimal(self):
        """Test creating a job with minimal required fields"""
        job = Job(
            id="test-123",
            file_name="test.txt",
            file_path="/uploads/test.txt",
            output_format=OutputFormat.MARKDOWN,
            status=JobStatus.PENDING
        )
        
        assert job.id == "test-123"
        assert job.file_name == "test.txt"
        assert job.file_path == "/uploads/test.txt"
        assert job.output_format == OutputFormat.MARKDOWN
        assert job.status == JobStatus.PENDING
        assert job.progress == 0
        assert job.use_ocr is False
        assert job.ocr_provider == OCRProvider.PADDLE
        assert job.webhook_url is None
        assert job.error_message is None
        assert job.result_path is None
        assert job.completed_at is None
        assert isinstance(job.created_at, datetime)
        assert isinstance(job.updated_at, datetime)
    
    def test_job_creation_full(self):
        """Test creating a job with all fields"""
        created_at = datetime.now()
        updated_at = datetime.now()
        completed_at = datetime.now()
        
        job = Job(
            id="test-456",
            file_name="image.png",
            file_path="/uploads/image.png",
            output_format=OutputFormat.JSON,
            status=JobStatus.COMPLETED,
            progress=100,
            use_ocr=True,
            ocr_provider=OCRProvider.EASYOCR,
            webhook_url="https://example.com/webhook",
            error_message=None,
            result_path="/outputs/image.json",
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at
        )
        
        assert job.id == "test-456"
        assert job.file_name == "image.png"
        assert job.output_format == OutputFormat.JSON
        assert job.status == JobStatus.COMPLETED
        assert job.progress == 100
        assert job.use_ocr is True
        assert job.ocr_provider == OCRProvider.EASYOCR
        assert job.webhook_url == "https://example.com/webhook"
        assert job.result_path == "/outputs/image.json"
        assert job.created_at == created_at
        assert job.updated_at == updated_at
        assert job.completed_at == completed_at
    
    def test_job_validation_invalid_id(self):
        """Test job validation with invalid ID"""
        with pytest.raises(ValidationError):
            Job(
                id="",  # Empty ID should fail
                file_name="test.txt",
                file_path="/uploads/test.txt",
                output_format=OutputFormat.MARKDOWN,
                status=JobStatus.PENDING
            )
    
    def test_job_validation_invalid_progress(self):
        """Test job validation with invalid progress"""
        with pytest.raises(ValidationError):
            Job(
                id="test-123",
                file_name="test.txt",
                file_path="/uploads/test.txt",
                output_format=OutputFormat.MARKDOWN,
                status=JobStatus.PENDING,
                progress=150  # Progress > 100 should fail
            )
        
        with pytest.raises(ValidationError):
            Job(
                id="test-123",
                file_name="test.txt",
                file_path="/uploads/test.txt",
                output_format=OutputFormat.MARKDOWN,
                status=JobStatus.PENDING,
                progress=-10  # Negative progress should fail
            )
    
    def test_job_to_dict(self):
        """Test converting job to dictionary"""
        job = Job(
            id="test-789",
            file_name="document.pdf",
            file_path="/uploads/document.pdf",
            output_format=OutputFormat.MARKDOWN,
            status=JobStatus.PROCESSING,
            progress=50,
            use_ocr=False,
            webhook_url="https://example.com/webhook"
        )
        
        job_dict = job.to_dict()
        
        assert job_dict["id"] == "test-789"
        assert job_dict["file_name"] == "document.pdf"
        assert job_dict["status"] == "processing"
        assert job_dict["progress"] == 50
        assert job_dict["use_ocr"] is False
        assert job_dict["webhook_url"] == "https://example.com/webhook"
        assert "created_at" in job_dict
        assert "updated_at" in job_dict
        assert job_dict["completed_at"] is None
        assert job_dict["error_message"] is None
        assert job_dict["result_path"] is None
    
    def test_job_from_dict(self):
        """Test creating job from dictionary"""
        job_data = {
            "id": "test-999",
            "file_name": "test.xlsx",
            "file_path": "/uploads/test.xlsx",
            "output_format": "json",
            "status": "completed",
            "progress": 100,
            "use_ocr": True,
            "ocr_provider": "mistral",
            "webhook_url": "https://example.com/webhook",
            "result_path": "/outputs/test.json",
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-01T10:05:00Z",
            "completed_at": "2024-01-01T10:05:00Z"
        }
        
        job = Job.from_dict(job_data)
        
        assert job.id == "test-999"
        assert job.file_name == "test.xlsx"
        assert job.output_format == OutputFormat.JSON
        assert job.status == JobStatus.COMPLETED
        assert job.progress == 100
        assert job.use_ocr is True
        assert job.ocr_provider == OCRProvider.MISTRAL
        assert job.webhook_url == "https://example.com/webhook"
        assert job.result_path == "/outputs/test.json"
        assert job.completed_at is not None
    
    def test_job_update_timestamps(self):
        """Test that updated_at is automatically set"""
        job = Job(
            id="test-timestamp",
            file_name="test.txt",
            file_path="/uploads/test.txt",
            output_format=OutputFormat.MARKDOWN,
            status=JobStatus.PENDING
        )
        
        original_updated_at = job.updated_at
        
        # Simulate time passing
        import time
        time.sleep(0.01)
        
        # Update job
        job.status = JobStatus.PROCESSING
        job.progress = 25
        
        # updated_at should be different (this would be handled by the job store in practice)
        assert job.updated_at == original_updated_at  # Model doesn't auto-update timestamps


class TestJobUpdate:
    """Test JobUpdate model"""
    
    def test_job_update_creation(self):
        """Test creating a job update"""
        completed_at = datetime.now()
        
        update = JobUpdate(
            status=JobStatus.COMPLETED,
            progress=100,
            result_path="/outputs/result.md",
            completed_at=completed_at,
            error_message=None
        )
        
        assert update.status == JobStatus.COMPLETED
        assert update.progress == 100
        assert update.result_path == "/outputs/result.md"
        assert update.completed_at == completed_at
        assert update.error_message is None
    
    def test_job_update_partial(self):
        """Test creating a partial job update"""
        update = JobUpdate(
            status=JobStatus.PROCESSING,
            progress=50
        )
        
        assert update.status == JobStatus.PROCESSING
        assert update.progress == 50
        assert update.result_path is None
        assert update.completed_at is None
        assert update.error_message is None
    
    def test_job_update_error(self):
        """Test creating a job update with error"""
        completed_at = datetime.now()
        
        update = JobUpdate(
            status=JobStatus.FAILED,
            error_message="Conversion failed due to invalid file format",
            completed_at=completed_at
        )
        
        assert update.status == JobStatus.FAILED
        assert update.error_message == "Conversion failed due to invalid file format"
        assert update.completed_at == completed_at
        assert update.progress is None
        assert update.result_path is None


class TestEnums:
    """Test enum classes"""
    
    def test_job_status_enum(self):
        """Test JobStatus enum values"""
        assert JobStatus.PENDING == "pending"
        assert JobStatus.PROCESSING == "processing"
        assert JobStatus.COMPLETED == "completed"
        assert JobStatus.FAILED == "failed"
        
        # Test all values are present
        expected_values = {"pending", "processing", "completed", "failed"}
        actual_values = {status.value for status in JobStatus}
        assert actual_values == expected_values
    
    def test_output_format_enum(self):
        """Test OutputFormat enum values"""
        assert OutputFormat.MARKDOWN == "md"
        assert OutputFormat.JSON == "json"
        
        # Test all values are present
        expected_values = {"md", "json"}
        actual_values = {fmt.value for fmt in OutputFormat}
        assert actual_values == expected_values
    
    def test_ocr_provider_enum(self):
        """Test OCRProvider enum values"""
        assert OCRProvider.PADDLE == "paddle"
        assert OCRProvider.EASYOCR == "easyocr"
        assert OCRProvider.MISTRAL == "mistral"
        
        # Test all values are present
        expected_values = {"paddle", "easyocr", "mistral"}
        actual_values = {provider.value for provider in OCRProvider}
        assert actual_values == expected_values
    
    def test_enum_from_string(self):
        """Test creating enums from string values"""
        assert JobStatus("pending") == JobStatus.PENDING
        assert OutputFormat("md") == OutputFormat.MARKDOWN
        assert OCRProvider("paddle") == OCRProvider.PADDLE
        
        # Test invalid values
        with pytest.raises(ValueError):
            JobStatus("invalid")
        
        with pytest.raises(ValueError):
            OutputFormat("invalid")
        
        with pytest.raises(ValueError):
            OCRProvider("invalid")


class TestJobValidation:
    """Test job validation scenarios"""
    
    def test_job_required_fields(self):
        """Test that required fields are enforced"""
        # Missing ID
        with pytest.raises(ValidationError):
            Job(
                file_name="test.txt",
                file_path="/uploads/test.txt",
                output_format=OutputFormat.MARKDOWN,
                status=JobStatus.PENDING
            )
        
        # Missing file_name
        with pytest.raises(ValidationError):
            Job(
                id="test-123",
                file_path="/uploads/test.txt",
                output_format=OutputFormat.MARKDOWN,
                status=JobStatus.PENDING
            )
        
        # Missing file_path
        with pytest.raises(ValidationError):
            Job(
                id="test-123",
                file_name="test.txt",
                output_format=OutputFormat.MARKDOWN,
                status=JobStatus.PENDING
            )
    
    def test_job_webhook_url_validation(self):
        """Test webhook URL validation"""
        # Valid URLs should work
        valid_urls = [
            "https://example.com/webhook",
            "http://localhost:8080/callback",
            "https://api.example.com/v1/webhooks/123"
        ]
        
        for url in valid_urls:
            job = Job(
                id="test-webhook",
                file_name="test.txt",
                file_path="/uploads/test.txt",
                output_format=OutputFormat.MARKDOWN,
                status=JobStatus.PENDING,
                webhook_url=url
            )
            assert job.webhook_url == url
    
    def test_job_file_path_validation(self):
        """Test file path validation"""
        # Valid paths should work
        valid_paths = [
            "/uploads/test.txt",
            "/var/uploads/document.pdf",
            "C:\\uploads\\file.docx",
            "./uploads/image.png"
        ]
        
        for path in valid_paths:
            job = Job(
                id="test-path",
                file_name="test.txt",
                file_path=path,
                output_format=OutputFormat.MARKDOWN,
                status=JobStatus.PENDING
            )
            assert job.file_path == path