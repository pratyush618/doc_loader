from typing import Optional, BinaryIO
import re
from striprtf.striprtf import rtf_to_text

from ..core.exceptions import ConversionException
from .base import BaseConverter, ConverterResult


class RTFConverter(BaseConverter):
    """Converter for Rich Text Format (RTF) files"""
    
    def accepts(self, file: BinaryIO, mimetype: Optional[str] = None,
                extension: Optional[str] = None) -> bool:
        """Check if this is an RTF file"""
        if extension and extension.lower() == '.rtf':
            return True
        
        if mimetype and mimetype in {
            'application/rtf',
            'text/rtf',
            'text/richtext'
        }:
            return True
        
        # Check RTF magic header
        try:
            content = file.read(10)
            # RTF files start with {\rtf
            return content.startswith(b'{\\rtf')
        except Exception:
            return False
        finally:
            self._reset_file_position(file)
    
    async def convert(self, file: BinaryIO, **kwargs) -> ConverterResult:
        """Convert RTF to markdown"""
        try:
            # Read RTF content
            rtf_content = file.read().decode('utf-8', errors='replace')
            
            # Convert RTF to plain text
            plain_text = rtf_to_text(rtf_content)
            
            # Convert to markdown
            markdown_content = await self._text_to_markdown(plain_text)
            
            # Extract title from first line
            title = None
            if markdown_content.strip():
                lines = markdown_content.split('\n')
                for line in lines:
                    clean_line = line.strip().replace('#', '').strip()
                    if clean_line:
                        title = clean_line[:100]  # First 100 chars
                        break
            
            return ConverterResult(
                content=markdown_content,
                title=title
            )
            
        except Exception as e:
            raise ConversionException(f"Failed to convert RTF: {str(e)}")
    
    async def _text_to_markdown(self, text: str) -> str:
        """Convert plain text to markdown with basic formatting"""
        if not text.strip():
            return ""
        
        # Split into lines
        lines = text.split('\n')
        markdown_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                markdown_lines.append("")
                continue
            
            # Check for potential headings (lines that are short and don't end with punctuation)
            if (len(line) < 50 and 
                not line.endswith(('.', '!', '?', ':', ';', ',')) and
                not line.startswith(('•', '-', '*', '1.', '2.', '3.', '4.', '5.'))):
                # Check if next line is empty or significantly longer (potential heading)
                markdown_lines.append(f"## {line}")
            else:
                # Check for bullet points
                if line.startswith(('•', '-', '*')):
                    # Convert to markdown list
                    clean_line = line.lstrip('•-* ').strip()
                    markdown_lines.append(f"- {clean_line}")
                elif re.match(r'^\d+\.', line):
                    # Convert numbered list
                    clean_line = re.sub(r'^\d+\.\s*', '', line)
                    markdown_lines.append(f"1. {clean_line}")
                else:
                    # Regular paragraph
                    markdown_lines.append(line)
        
        return '\n'.join(markdown_lines)