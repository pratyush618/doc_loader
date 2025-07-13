class DocumentConverterException(Exception):
    """Base exception for document converter"""
    pass


class UnsupportedFormatException(DocumentConverterException):
    """Raised when a document format is not supported"""
    def __init__(self, format_type: str, message: str = None):
        self.format_type = format_type
        super().__init__(message or f"Unsupported format: {format_type}")


class ConversionException(DocumentConverterException):
    """Raised when document conversion fails"""
    pass


class FileSizeException(DocumentConverterException):
    """Raised when file size exceeds limits"""
    def __init__(self, size: int, max_size: int):
        self.size = size
        self.max_size = max_size
        super().__init__(f"File size {size} exceeds maximum allowed size {max_size}")


class WebhookException(DocumentConverterException):
    """Raised when webhook notification fails"""
    pass


class JobNotFoundException(DocumentConverterException):
    """Raised when a job is not found"""
    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(f"Job {job_id} not found")