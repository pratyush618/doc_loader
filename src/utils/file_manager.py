import tempfile
import shutil
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
import threading
import atexit

logger = logging.getLogger(__name__)


class TempFileManager:
    """Manages temporary files with TTL and automatic cleanup."""
    
    def __init__(self, base_upload_dir: str = "uploads", base_output_dir: str = "outputs", 
                 default_ttl_hours: int = 24):
        """
        Initialize the temporary file manager.
        
        Args:
            base_upload_dir: Base directory for uploads
            base_output_dir: Base directory for outputs
            default_ttl_hours: Default TTL in hours for abandoned files
        """
        self.base_upload_dir = Path(base_upload_dir)
        self.base_output_dir = Path(base_output_dir)
        self.default_ttl = timedelta(hours=default_ttl_hours)
        self.file_registry: Dict[str, Tuple[Path, datetime]] = {}
        
        # Create base directories if they don't exist
        self.base_upload_dir.mkdir(exist_ok=True)
        self.base_output_dir.mkdir(exist_ok=True)
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        
        # Register cleanup on exit
        atexit.register(self._cleanup_on_exit)
    
    def create_temp_upload_file(self, suffix: Optional[str] = None, 
                               prefix: str = "upload_") -> Tuple[int, str]:
        """
        Create a temporary file for uploads.
        
        Args:
            suffix: File suffix/extension (e.g., '.pdf')
            prefix: File prefix
            
        Returns:
            Tuple of (file descriptor, file path)
        """
        fd, temp_path = tempfile.mkstemp(
            suffix=suffix,
            prefix=prefix,
            dir=str(self.base_upload_dir)
        )
        
        # Register file with current timestamp
        self.file_registry[temp_path] = (Path(temp_path), datetime.now())
        logger.info(f"Created temporary upload file: {temp_path}")
        
        return fd, temp_path
    
    def create_temp_output_file(self, suffix: Optional[str] = None,
                               prefix: str = "output_") -> Tuple[int, str]:
        """
        Create a temporary file for outputs.
        
        Args:
            suffix: File suffix/extension (e.g., '.md')
            prefix: File prefix
            
        Returns:
            Tuple of (file descriptor, file path)
        """
        fd, temp_path = tempfile.mkstemp(
            suffix=suffix,
            prefix=prefix,
            dir=str(self.base_output_dir)
        )
        
        # Register file with current timestamp
        self.file_registry[temp_path] = (Path(temp_path), datetime.now())
        logger.info(f"Created temporary output file: {temp_path}")
        
        return fd, temp_path
    
    def create_temp_upload_dir(self, suffix: Optional[str] = None,
                              prefix: str = "upload_dir_") -> str:
        """
        Create a temporary directory for uploads.
        
        Args:
            suffix: Directory suffix
            prefix: Directory prefix
            
        Returns:
            Path to the created directory
        """
        temp_dir = tempfile.mkdtemp(
            suffix=suffix,
            prefix=prefix,
            dir=str(self.base_upload_dir)
        )
        
        # Register directory with current timestamp
        self.file_registry[temp_dir] = (Path(temp_dir), datetime.now())
        logger.info(f"Created temporary upload directory: {temp_dir}")
        
        return temp_dir
    
    def create_temp_output_dir(self, suffix: Optional[str] = None,
                              prefix: str = "output_dir_") -> str:
        """
        Create a temporary directory for outputs.
        
        Args:
            suffix: Directory suffix
            prefix: Directory prefix
            
        Returns:
            Path to the created directory
        """
        temp_dir = tempfile.mkdtemp(
            suffix=suffix,
            prefix=prefix,
            dir=str(self.base_output_dir)
        )
        
        # Register directory with current timestamp
        self.file_registry[temp_dir] = (Path(temp_dir), datetime.now())
        logger.info(f"Created temporary output directory: {temp_dir}")
        
        return temp_dir
    
    def mark_for_deletion(self, file_path: str) -> bool:
        """
        Mark a file for immediate deletion.
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            path = Path(file_path)
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                
                # Remove from registry
                if file_path in self.file_registry:
                    del self.file_registry[file_path]
                
                logger.info(f"Successfully deleted: {file_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: {file_path}")
                return False
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return False
    
    def cleanup_old_files(self, ttl: Optional[timedelta] = None) -> int:
        """
        Clean up files older than the specified TTL.
        
        Args:
            ttl: Time-to-live for files. Uses default if not specified.
            
        Returns:
            Number of files cleaned up
        """
        ttl = ttl or self.default_ttl
        current_time = datetime.now()
        files_cleaned = 0
        
        # Clean registered files
        files_to_remove = []
        for file_path, (path, created_time) in self.file_registry.items():
            if current_time - created_time > ttl:
                try:
                    if path.exists():
                        if path.is_dir():
                            shutil.rmtree(path)
                        else:
                            path.unlink()
                        files_cleaned += 1
                    files_to_remove.append(file_path)
                except Exception as e:
                    logger.error(f"Error cleaning up {file_path}: {e}")
        
        # Remove from registry
        for file_path in files_to_remove:
            del self.file_registry[file_path]
        
        # Also clean unregistered old files
        for base_dir in [self.base_upload_dir, self.base_output_dir]:
            for item in base_dir.iterdir():
                try:
                    # Get file modification time
                    mtime = datetime.fromtimestamp(item.stat().st_mtime)
                    if current_time - mtime > ttl:
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()
                        files_cleaned += 1
                        logger.info(f"Cleaned up old file: {item}")
                except Exception as e:
                    logger.error(f"Error cleaning up {item}: {e}")
        
        if files_cleaned > 0:
            logger.info(f"Cleaned up {files_cleaned} old files/directories")
        
        return files_cleaned
    
    def _cleanup_loop(self):
        """Background thread that periodically cleans up old files."""
        while True:
            try:
                # Run cleanup every hour
                time.sleep(3600)
                self.cleanup_old_files()
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    def _cleanup_on_exit(self):
        """Clean up temporary files on program exit."""
        try:
            # Only clean up files created in this session
            for file_path, (path, _) in self.file_registry.items():
                try:
                    if path.exists():
                        if path.is_dir():
                            shutil.rmtree(path)
                        else:
                            path.unlink()
                except Exception as e:
                    logger.error(f"Error cleaning up {file_path} on exit: {e}")
        except Exception as e:
            logger.error(f"Error in cleanup on exit: {e}")


# Global instance
_temp_file_manager: Optional[TempFileManager] = None


def get_temp_file_manager(base_upload_dir: str = "uploads", 
                         base_output_dir: str = "outputs",
                         default_ttl_hours: int = 24) -> TempFileManager:
    """
    Get the global TempFileManager instance.
    
    Args:
        base_upload_dir: Base directory for uploads
        base_output_dir: Base directory for outputs
        default_ttl_hours: Default TTL in hours
        
    Returns:
        TempFileManager instance
    """
    global _temp_file_manager
    if _temp_file_manager is None:
        _temp_file_manager = TempFileManager(
            base_upload_dir=base_upload_dir,
            base_output_dir=base_output_dir,
            default_ttl_hours=default_ttl_hours
        )
    return _temp_file_manager