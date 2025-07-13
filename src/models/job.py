from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OutputFormat(str, Enum):
    MARKDOWN = "md"
    JSON = "json"


class OCRProvider(str, Enum):
    PADDLE = "paddle"
    MISTRAL = "mistral"
    EASY_OCR = "easyocr"


class JobCreate(BaseModel):
    file_name: str
    file_path: str
    output_format: OutputFormat = OutputFormat.MARKDOWN
    webhook_url: Optional[str] = None
    use_ocr: bool = False
    ocr_provider: OCRProvider = OCRProvider.PADDLE
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class JobUpdate(BaseModel):
    status: Optional[JobStatus] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    result_path: Optional[str] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None


class Job(BaseModel):
    id: str
    file_name: str
    file_path: str
    output_format: OutputFormat
    status: JobStatus = JobStatus.PENDING
    progress: int = 0
    webhook_url: Optional[str] = None
    use_ocr: bool = False
    ocr_provider: OCRProvider = OCRProvider.PADDLE
    result_path: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class JobResponse(BaseModel):
    id: str
    status: JobStatus
    progress: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    result_url: Optional[str] = None
    error_message: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConversionResult(BaseModel):
    content: str
    format: OutputFormat
    metadata: Dict[str, Any] = Field(default_factory=dict)
    images: Optional[Dict[str, str]] = None  # filename -> base64 encoded image