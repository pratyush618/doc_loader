from typing import Optional, BinaryIO
import chardet

from ..core.exceptions import ConversionException
from .base import BaseConverter, ConverterResult


class TextConverter(BaseConverter):
    """Converter for plain text files"""
    
    TEXT_EXTENSIONS = {'.txt', '.text', '.log', '.md', '.markdown', '.rst'}
    TEXT_MIMETYPES = {
        'text/plain',
        'text/markdown',
        'text/x-markdown',
        'text/x-rst',
        'text/restructuredtext'
    }
    
    def accepts(self, file: BinaryIO, mimetype: Optional[str] = None,
                extension: Optional[str] = None) -> bool:
        """Check if this is a text file"""
        if extension and extension in self.TEXT_EXTENSIONS:
            return True
        
        if mimetype and mimetype in self.TEXT_MIMETYPES:
            return True
        
        # Try to detect by reading first few bytes
        try:
            chunk = file.read(1024)
            if chunk:
                # Detect encoding
                detection = chardet.detect(chunk)
                if detection['confidence'] > 0.7:
                    return True
        except Exception:
            pass
        finally:
            self._reset_file_position(file)
        
        return False
    
    async def convert(self, file: BinaryIO, **kwargs) -> ConverterResult:
        """Convert text file to markdown"""
        try:
            # Read entire file
            content = file.read()
            
            # Detect encoding
            detection = chardet.detect(content)
            encoding = detection['encoding'] or 'utf-8'
            
            # Decode content
            text = content.decode(encoding, errors='replace')
            
            # For markdown files, return as-is
            if kwargs.get('extension') in {'.md', '.markdown'}:
                return ConverterResult(
                    content=text
                )
            
            # For other text files, wrap in code block if needed
            if kwargs.get('preserve_formatting', True):
                markdown = f"```\n{text}\n```"
            else:
                markdown = text
            
            return ConverterResult(
                content=markdown
            )
            
        except Exception as e:
            raise ConversionException(f"Failed to convert text file: {str(e)}")