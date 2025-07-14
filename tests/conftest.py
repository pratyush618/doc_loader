"""
Pytest configuration and shared fixtures
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import asyncio
import io
from PIL import Image

# Add src to Python path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.main import app
from src.models.job import Job, JobStatus, OutputFormat, OCRProvider


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_pdf_file():
    """Create a sample PDF file for testing"""
    content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    return io.BytesIO(content)


@pytest.fixture
def sample_text_file():
    """Create a sample text file for testing"""
    content = b"This is a sample text file for testing.\nIt has multiple lines.\nAnd some content."
    return io.BytesIO(content)


@pytest.fixture
def sample_image_file():
    """Create a sample image file for testing"""
    # Create a simple 100x100 red image
    img = Image.new('RGB', (100, 100), color='red')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


@pytest.fixture
def sample_job():
    """Create a sample job for testing"""
    return Job(
        id="test-job-123",
        file_name="test.pdf",
        file_path="/uploads/test.pdf",
        output_format=OutputFormat.MARKDOWN,
        status=JobStatus.PENDING,
        progress=0,
        webhook_url="http://example.com/webhook",
        use_ocr=False,
        ocr_provider=OCRProvider.PADDLE
    )


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    with patch('src.services.job_store.redis') as mock:
        mock_client = Mock()
        mock.from_url.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_celery():
    """Mock Celery task"""
    with patch('src.services.tasks.convert_document') as mock:
        mock.delay = Mock(return_value=Mock(id="celery-task-123"))
        yield mock


@pytest.fixture
def mock_storage():
    """Mock storage service"""
    with patch('src.services.storage.storage') as mock:
        mock.save_file = Mock(return_value="/uploads/test-file.pdf")
        mock.read_file = Mock(return_value=b"file content")
        mock.save_result = Mock(return_value="/outputs/result.md")
        mock.get_result_url = Mock(return_value="http://localhost:8000/api/v1/jobs/123/result")
        yield mock


@pytest.fixture
def mock_ocr_service():
    """Mock OCR service"""
    with patch('src.services.ocr_service.ocr_service') as mock:
        from src.services.ocr_service import OCRResult
        mock.extract_text = Mock(return_value=OCRResult(
            text="Extracted text from image",
            confidence=0.95,
            metadata={"provider": "paddle", "lines_detected": 1}
        ))
        mock.get_available_providers = Mock(return_value=["paddle", "easyocr"])
        yield mock


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()