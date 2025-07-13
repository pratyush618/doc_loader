import os
import aiofiles
import hashlib
from pathlib import Path
from typing import Optional, BinaryIO
from datetime import datetime

from ..core.config import settings
from ..core.exceptions import FileSizeException
from ..utils.temp_file_manager import get_temp_file_manager


class StorageService:
    """Service for handling file storage"""
    
    def __init__(self):
        self.upload_dir = Path(settings.upload_dir)
        self.output_dir = Path(settings.output_dir)
        
        # Create directories if they don't exist
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize temp file manager
        self.temp_manager = get_temp_file_manager(
            base_upload_dir=str(self.upload_dir),
            base_output_dir=str(self.output_dir),
            default_ttl_hours=settings.file_ttl_hours
        )
    
    async def save_upload(self, file_data: bytes, filename: str) -> str:
        """
        Save uploaded file and return its path.
        
        Args:
            file_data: File content
            filename: Original filename
            
        Returns:
            Path to saved file
            
        Raises:
            FileSizeException: If file exceeds size limit
        """
        # Check file size
        if len(file_data) > settings.max_file_size:
            raise FileSizeException(len(file_data), settings.max_file_size)
        
        # Extract file extension
        suffix = Path(filename).suffix if filename else None
        
        # Create temporary file
        fd, temp_path = self.temp_manager.create_temp_upload_file(
            suffix=suffix,
            prefix=f"upload_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_"
        )
        
        try:
            # Write data to temp file
            with os.fdopen(fd, 'wb') as f:
                f.write(file_data)
            
            return temp_path
        except Exception:
            # Clean up on error
            os.close(fd)
            self.temp_manager.mark_for_deletion(temp_path)
            raise
    
    async def save_result(self, job_id: str, content: str, format: str) -> str:
        """
        Save conversion result and return its path.
        
        Args:
            job_id: Job ID
            content: Converted content
            format: Output format (md or json)
            
        Returns:
            Path to saved result
        """
        # Create temporary output file
        fd, temp_path = self.temp_manager.create_temp_output_file(
            suffix=f".{format}",
            prefix=f"output_{job_id}_"
        )
        
        try:
            # Close file descriptor and write content
            os.close(fd)
            async with aiofiles.open(temp_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            return temp_path
        except Exception:
            # Clean up on error
            self.temp_manager.mark_for_deletion(temp_path)
            raise
    
    async def read_file(self, file_path: str) -> bytes:
        """Read file content"""
        async with aiofiles.open(file_path, 'rb') as f:
            return await f.read()
    
    async def delete_file(self, file_path: str) -> None:
        """Delete a file if it exists"""
        self.temp_manager.mark_for_deletion(file_path)
    
    def get_result_url(self, job_id: str, format: str) -> str:
        """Generate URL for result file"""
        return f"{settings.api_prefix}/jobs/{job_id}/result"