from typing import Dict, Type, Optional, BinaryIO, List
import mimetypes
from pathlib import Path

from ..core.exceptions import UnsupportedFormatException
from .base import BaseConverter


class ConverterRegistry:
    """Registry for document converters"""
    
    def __init__(self):
        self._converters: List[Type[BaseConverter]] = []
        self._instances: Dict[Type[BaseConverter], BaseConverter] = {}
    
    def register(self, converter_class: Type[BaseConverter]) -> None:
        """Register a converter class"""
        if converter_class not in self._converters:
            self._converters.append(converter_class)
    
    def get_converter(self, file: BinaryIO, filename: Optional[str] = None,
                     mimetype: Optional[str] = None) -> BaseConverter:
        """
        Get appropriate converter for the file.
        
        Args:
            file: File-like object
            filename: Original filename
            mimetype: MIME type
            
        Returns:
            Converter instance
            
        Raises:
            UnsupportedFormatException: If no converter found
        """
        # Determine extension and mimetype
        extension = None
        if filename:
            extension = Path(filename).suffix.lower()
            if not mimetype:
                mimetype, _ = mimetypes.guess_type(filename)
        
        # Find appropriate converter
        for converter_class in self._converters:
            # Get or create instance
            if converter_class not in self._instances:
                self._instances[converter_class] = converter_class()
            
            converter = self._instances[converter_class]
            
            # Check if converter accepts this file
            if converter.accepts(file, mimetype=mimetype, extension=extension):
                file.seek(0)  # Reset position after checking
                return converter
        
        # No converter found
        format_info = []
        if filename:
            format_info.append(f"filename={filename}")
        if extension:
            format_info.append(f"extension={extension}")
        if mimetype:
            format_info.append(f"mimetype={mimetype}")
        
        raise UnsupportedFormatException(
            format_type=", ".join(format_info) if format_info else "unknown"
        )


# Global registry instance
_registry = ConverterRegistry()


def get_converter_registry() -> ConverterRegistry:
    """Get the global converter registry"""
    return _registry