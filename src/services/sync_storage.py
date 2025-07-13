import os
import hashlib
from pathlib import Path
from datetime import datetime

from ..core.config import settings
from ..core.exceptions import FileSizeException


class SyncStorageService:
    """Synchronous storage service"""
    
    def __init__(self):
        # Convert to absolute paths and resolve properly
        if os.path.isabs(settings.upload_dir):
            self.upload_dir = Path(settings.upload_dir)
        else:
            # Use project root as base for relative paths
            project_root = Path(__file__).parent.parent.parent
            self.upload_dir = project_root / settings.upload_dir
        
        if os.path.isabs(settings.output_dir):
            self.output_dir = Path(settings.output_dir)
        else:
            # Use project root as base for relative paths
            project_root = Path(__file__).parent.parent.parent
            self.output_dir = project_root / settings.output_dir
        
        # Create directories if they don't exist
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Upload directory: {self.upload_dir}")
        print(f"Output directory: {self.output_dir}")
    
    def save_upload(self, file_data: bytes, filename: str) -> str:
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
        
        # Generate unique filename
        file_hash = hashlib.md5(file_data).hexdigest()
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file_hash}_{filename}"
        
        # Save file
        file_path = self.upload_dir / safe_filename
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        return str(file_path)
    
    def save_result(self, job_id: str, content: str, format: str) -> str:
        """
        Save conversion result and return its path.
        
        Args:
            job_id: Job ID
            content: Converted content
            format: Output format (md or json)
            
        Returns:
            Path to saved result
        """
        # Create result filename
        filename = f"{job_id}.{format}"
        file_path = self.output_dir / filename
        
        # Save result
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(file_path)
    
    def read_file(self, file_path: str) -> bytes:
        """Read file content"""
        # Convert to Path and resolve properly
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(path, 'rb') as f:
            return f.read()
    
    def delete_file(self, file_path: str) -> None:
        """Delete a file if it exists"""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
        except Exception:
            pass  # Ignore errors during cleanup
    
    def get_result_url(self, job_id: str, format: str) -> str:
        """Generate URL for result file"""
        return f"{settings.api_prefix}/jobs/{job_id}/result"


# Global sync instance
sync_storage = SyncStorageService()