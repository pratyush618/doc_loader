from typing import Optional, BinaryIO
import PyPDF2

from ..core.exceptions import ConversionException
from .base import BaseConverter, ConverterResult


class PDFConverter(BaseConverter):
    """Converter for PDF files"""
    
    def accepts(self, file: BinaryIO, mimetype: Optional[str] = None,
                extension: Optional[str] = None) -> bool:
        """Check if this is a PDF file"""
        if extension and extension.lower() == '.pdf':
            return True
        
        if mimetype and mimetype == 'application/pdf':
            return True
        
        # Check magic bytes
        try:
            magic = file.read(4)
            return magic == b'%PDF'
        except Exception:
            return False
        finally:
            self._reset_file_position(file)
    
    async def convert(self, file: BinaryIO, **kwargs) -> ConverterResult:
        """Convert PDF to markdown"""
        try:
            # Read PDF
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Extract text from all pages
            markdown_parts = []
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    text = page.extract_text()
                    if text.strip():
                        markdown_parts.append(f"## Page {page_num}\n\n{text}\n")
                except Exception as e:
                    markdown_parts.append(f"## Page {page_num}\n\n*Error extracting text: {str(e)}*\n")
            
            # Join all parts
            content = "\n".join(markdown_parts)
            
            # Try to extract title from first page content
            title = None
            if content.strip():
                # Get first line of content as title
                lines = content.split('\n')
                for line in lines:
                    clean_line = line.strip().replace('#', '').strip()
                    if clean_line and not clean_line.startswith('Page'):
                        title = clean_line[:100]  # First 100 chars
                        break
            
            return ConverterResult(
                content=content,
                title=title
            )
            
        except Exception as e:
            raise ConversionException(f"Failed to convert PDF: {str(e)}")