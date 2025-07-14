"""
Tests for API endpoints
"""
from fastapi import status
from unittest.mock import Mock, patch
from datetime import datetime

from src.models.job import JobStatus, OutputFormat


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_health_check(self, test_client):
        """Test basic health check endpoint"""
        response = test_client.get("/api/v1/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_ready_check_success(self, test_client, mock_redis):
        """Test readiness check when all services are available"""
        mock_redis.ping.return_value = True
        
        response = test_client.get("/api/v1/ready")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ready"
        assert data["services"]["redis"] is True
    
    def test_ready_check_redis_failure(self, test_client, mock_redis):
        """Test readiness check when Redis is unavailable"""
        mock_redis.ping.side_effect = Exception("Redis connection failed")
        
        response = test_client.get("/api/v1/ready")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "not ready"
        assert data["services"]["redis"] is False


class TestJobsEndpoints:
    """Test job-related endpoints"""
    
    def test_create_job_success(self, test_client, mock_storage, mock_celery):
        """Test successful job creation"""
        with patch('src.api.routes.jobs.job_store') as mock_job_store:
            mock_job_store.create.return_value = Mock(
                id="job-123",
                status=JobStatus.PENDING,
                progress=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            files = {"file": ("test.txt", b"Test content", "text/plain")}
            data = {
                "output_format": "md",
                "webhook_url": "http://example.com/webhook"
            }
            
            response = test_client.post("/api/v1/jobs", files=files, data=data)
            
            assert response.status_code == status.HTTP_200_OK
            result = response.json()
            assert result["id"] == "job-123"
            assert result["status"] == "pending"
            assert mock_celery.delay.called
    
    def test_create_job_invalid_format(self, test_client):
        """Test job creation with invalid output format"""
        files = {"file": ("test.txt", b"Test content", "text/plain")}
        data = {"output_format": "invalid"}
        
        response = test_client.post("/api/v1/jobs", files=files, data=data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_create_job_no_file(self, test_client):
        """Test job creation without file"""
        data = {"output_format": "md"}
        
        response = test_client.post("/api/v1/jobs", data=data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_create_job_file_too_large(self, test_client):
        """Test job creation with file exceeding size limit"""
        # Create a file larger than max size
        large_content = b"x" * (100 * 1024 * 1024 + 1)  # 100MB + 1 byte
        files = {"file": ("large.txt", large_content, "text/plain")}
        data = {"output_format": "md"}
        
        response = test_client.post("/api/v1/jobs", files=files, data=data)
        assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    
    def test_get_job_success(self, test_client):
        """Test getting job details"""
        with patch('src.api.routes.jobs.job_store') as mock_job_store:
            mock_job_store.get.return_value = Mock(
                id="job-123",
                status=JobStatus.COMPLETED,
                progress=100,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            
            response = test_client.get("/api/v1/jobs/job-123")
            
            assert response.status_code == status.HTTP_200_OK
            result = response.json()
            assert result["id"] == "job-123"
            assert result["status"] == "completed"
            assert result["progress"] == 100
    
    def test_get_job_not_found(self, test_client):
        """Test getting non-existent job"""
        with patch('src.api.routes.jobs.job_store') as mock_job_store:
            mock_job_store.get.return_value = None
            
            response = test_client.get("/api/v1/jobs/non-existent")
            assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_job_result_success(self, test_client, temp_dir):
        """Test downloading job result"""
        # Create a test result file
        result_file = temp_dir / "result.md"
        result_file.write_text("# Converted Document\n\nContent here")
        
        with patch('src.api.routes.jobs.job_store') as mock_job_store:
            mock_job = Mock(
                id="job-123",
                status=JobStatus.COMPLETED,
                result_path=str(result_file),
                file_name="original.pdf",
                output_format=OutputFormat.MARKDOWN
            )
            mock_job_store.get.return_value = mock_job
            
            response = test_client.get("/api/v1/jobs/job-123/result")
            
            assert response.status_code == status.HTTP_200_OK
            assert response.headers["content-type"] == "text/markdown; charset=utf-8"
            assert "attachment" in response.headers["content-disposition"]
            assert "original.md" in response.headers["content-disposition"]
            assert response.content == b"# Converted Document\n\nContent here"
    
    def test_get_job_result_not_completed(self, test_client):
        """Test downloading result for incomplete job"""
        with patch('src.api.routes.jobs.job_store') as mock_job_store:
            mock_job_store.get.return_value = Mock(
                id="job-123",
                status=JobStatus.PROCESSING
            )
            
            response = test_client.get("/api/v1/jobs/job-123/result")
            assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_get_job_result_file_not_found(self, test_client):
        """Test downloading result when file doesn't exist"""
        with patch('src.api.routes.jobs.job_store') as mock_job_store:
            mock_job_store.get.return_value = Mock(
                id="job-123",
                status=JobStatus.COMPLETED,
                result_path="/non/existent/file.md"
            )
            
            response = test_client.get("/api/v1/jobs/job-123/result")
            assert response.status_code == status.HTTP_404_NOT_FOUND


class TestJobCreationWithOCR:
    """Test job creation with OCR options"""
    
    def test_create_job_with_ocr_enabled(self, test_client, mock_storage, mock_celery):
        """Test job creation with OCR enabled"""
        with patch('src.api.routes.jobs.job_store') as mock_job_store:
            mock_job_store.create.return_value = Mock(
                id="job-123",
                status=JobStatus.PENDING,
                use_ocr=True,
                ocr_provider="paddle"
            )
            
            files = {"file": ("image.png", b"PNG content", "image/png")}
            data = {
                "output_format": "md",
                "use_ocr": "true",
                "ocr_provider": "paddle"
            }
            
            response = test_client.post("/api/v1/jobs", files=files, data=data)
            
            assert response.status_code == status.HTTP_200_OK
            # Verify that OCR options were passed to job creation
            create_call = mock_job_store.create.call_args[0][0]
            assert create_call.use_ocr is True
            assert create_call.ocr_provider.value == "paddle"
    
    def test_create_job_with_invalid_ocr_provider(self, test_client):
        """Test job creation with invalid OCR provider"""
        files = {"file": ("image.png", b"PNG content", "image/png")}
        data = {
            "output_format": "md",
            "use_ocr": "true",
            "ocr_provider": "invalid_provider"
        }
        
        response = test_client.post("/api/v1/jobs", files=files, data=data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY