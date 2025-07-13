from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, BinaryIO
from dataclasses import dataclass, field


@dataclass
class ConverterResult:
    """Result of document conversion"""
    content: str
    title: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    images: Dict[str, bytes] = field(default_factory=dict)  # filename -> image bytes
    
    @property
    def text_content(self) -> str:
        """Backward compatibility property"""
        return self.content


class BaseConverter(ABC):
    """Abstract base class for document converters"""
    
    @abstractmethod
    def accepts(self, file: BinaryIO, mimetype: Optional[str] = None, 
                extension: Optional[str] = None) -> bool:
        """
        Check if this converter can handle the given file.
        
        Args:
            file: File-like object to check
            mimetype: MIME type of the file
            extension: File extension
            
        Returns:
            True if this converter can handle the file, False otherwise
            
        Note:
            If the converter reads from the file to make this determination,
            it MUST seek back to the beginning before returning.
        """
        pass
    
    @abstractmethod
    async def convert(self, file: BinaryIO, **kwargs) -> ConverterResult:
        """
        Convert the file to markdown or structured format.
        
        Args:
            file: File-like object to convert
            **kwargs: Additional conversion options
            
        Returns:
            ConverterResult with converted content
            
        Raises:
            ConversionException: If conversion fails
        """
        pass
    
    def _reset_file_position(self, file: BinaryIO) -> None:
        """Helper to reset file position to beginning"""
        if hasattr(file, 'seek'):
            file.seek(0)