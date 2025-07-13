from typing import Optional, BinaryIO
import xlrd
from xlrd.biffh import XLRDError

from ..core.exceptions import ConversionException
from .base import BaseConverter, ConverterResult


class XLSConverter(BaseConverter):
    """Converter for Microsoft Excel XLS files (legacy format)"""
    
    def accepts(self, file: BinaryIO, mimetype: Optional[str] = None,
                extension: Optional[str] = None) -> bool:
        """Check if this is an XLS file"""
        if extension and extension.lower() == '.xls':
            return True
        
        if mimetype and mimetype in {
            'application/vnd.ms-excel',
            'application/excel',
            'application/x-excel',
            'application/x-msexcel'
        }:
            return True
        
        # Try to open with xlrd
        try:
            xlrd.open_workbook(file_contents=file.read())
            return True
        except (XLRDError, Exception):
            return False
        finally:
            self._reset_file_position(file)
    
    async def convert(self, file: BinaryIO, **kwargs) -> ConverterResult:
        """Convert XLS to markdown"""
        try:
            # Read the XLS file
            workbook = xlrd.open_workbook(file_contents=file.read())
            
            # Convert each sheet
            markdown_parts = []
            
            for sheet_idx in range(workbook.nsheets):
                sheet = workbook.sheet_by_index(sheet_idx)
                sheet_name = workbook.sheet_names()[sheet_idx]
                
                # Add sheet header
                markdown_parts.append(f"# Sheet: {sheet_name}\n")
                
                if sheet.nrows == 0:
                    markdown_parts.append("*Empty sheet*\n")
                    continue
                
                # Process sheet data
                sheet_md = await self._convert_sheet_to_markdown(sheet)
                markdown_parts.append(sheet_md)
                markdown_parts.append("\n")
            
            content = "\n".join(markdown_parts)
            
            # Create title based on sheet count
            title = f"Excel Workbook ({workbook.nsheets} sheets)"
            
            return ConverterResult(
                content=content,
                title=title
            )
            
        except Exception as e:
            raise ConversionException(f"Failed to convert XLS: {str(e)}")
    
    async def _convert_sheet_to_markdown(self, sheet) -> str:
        """Convert a single sheet to markdown table"""
        if sheet.nrows == 0:
            return "*Empty sheet*"
        
        # Collect all rows with data
        rows = []
        max_col = 0
        
        for row_idx in range(sheet.nrows):
            row_data = []
            has_data = False
            
            for col_idx in range(sheet.ncols):
                cell_value = sheet.cell_value(row_idx, col_idx)
                formatted_value = self._format_cell_value(cell_value)
                row_data.append(formatted_value)
                
                if formatted_value.strip():  # Non-empty cell
                    has_data = True
            
            # Only include rows that have at least one non-empty cell
            if has_data:
                rows.append(row_data)
                max_col = max(max_col, len(row_data))
        
        if not rows:
            return "*No data in sheet*"
        
        # Ensure all rows have the same number of columns
        for row in rows:
            while len(row) < max_col:
                row.append("")
        
        # Create markdown table
        markdown_lines = []
        
        # If we have at least one row, treat first row as header
        if rows:
            header = rows[0]
            
            # Create header row
            markdown_lines.append("| " + " | ".join(header) + " |")
            
            # Create separator row
            separators = []
            for cell in header:
                # Make separator at least 3 characters wide
                width = max(len(cell), 3)
                separators.append("-" * width)
            markdown_lines.append("| " + " | ".join(separators) + " |")
            
            # Add data rows
            for row in rows[1:]:
                markdown_lines.append("| " + " | ".join(row) + " |")
        
        return "\n".join(markdown_lines)
    
    def _format_cell_value(self, value) -> str:
        """Format cell value for markdown"""
        if value is None or value == "":
            return ""
        
        # Handle different data types
        if isinstance(value, bool):
            return str(value)
        elif isinstance(value, (int, float)):
            # Format numbers
            if isinstance(value, float) and value.is_integer():
                return str(int(value))
            return str(value)
        else:
            # Convert to string and escape pipe characters
            str_value = str(value)
            return str_value.replace("|", "\\|").replace("\n", " ").replace("\r", "")