import io
import json
import base64
from datetime import datetime
from pathlib import Path

from celery import Task
from .celery_app import celery_app
from ..core.exceptions import ConversionException
from ..models.job import JobStatus, JobUpdate, OutputFormat
from ..converters import get_converter_registry
from ..converters.text import TextConverter
from ..converters.pdf import PDFConverter
from ..converters.image import ImageConverter
from ..converters.docx import DocxConverter
from ..converters.pptx import PPTXConverter
from ..converters.xls import XLSConverter
from ..converters.xlsx import XLSXConverter
from ..converters.rtf import RTFConverter
from .sync_storage import sync_storage
from .sync_job_store import sync_job_store
from .sync_webhook import sync_webhook_service


# Register converters
registry = get_converter_registry()
registry.register(TextConverter)
registry.register(PDFConverter)
registry.register(ImageConverter)
registry.register(DocxConverter)
registry.register(PPTXConverter)
registry.register(XLSConverter)
registry.register(XLSXConverter)
registry.register(RTFConverter)


class ConversionTask(Task):
    """Base task with error handling"""
    
    def update_job_progress(self, job_id: str, progress: int):
        """Update job progress"""
        sync_job_store.update(job_id, JobUpdate(progress=progress))
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        job_id = args[0] if args else None
        if job_id:
            try:
                self._handle_failure_sync(job_id, exc)
            except Exception as e:
                print(f"Failed to handle task failure: {e}")
    
    def _handle_failure_sync(self, job_id: str, exc: Exception):
        """Sync implementation of failure handling"""
        try:
            sync_job_store.update(
                job_id,
                JobUpdate(
                    status=JobStatus.FAILED,
                    error_message=str(exc),
                    completed_at=datetime.utcnow()
                )
            )
            
            # Send webhook notification
            job = sync_job_store.get(job_id)
            sync_webhook_service.notify_job_status(job)
        except Exception as e:
            print(f"Failed to send webhook notification: {e}")


@celery_app.task(bind=True, base=ConversionTask, name='convert_document')
def convert_document(self, job_id: str) -> dict:
    """
    Celery task to convert a document.
    
    Args:
        job_id: Job ID
        
    Returns:
        Conversion result
    """
    return _convert_document_sync(self, job_id)


def _convert_document_sync(task: ConversionTask, job_id: str) -> dict:
    """Sync implementation of document conversion"""
    try:
        # Get job details
        job = sync_job_store.get(job_id)
        
        # Update status to processing
        sync_job_store.update(
            job_id,
            JobUpdate(status=JobStatus.PROCESSING, progress=10)
        )
        
        # Read file
        file_data = sync_storage.read_file(job.file_path)
        file_obj = io.BytesIO(file_data)
        
        task.update_job_progress(job_id, 20)
        
        # Get appropriate converter
        converter = registry.get_converter(
            file_obj,
            filename=job.file_name,
            mimetype=None
        )
        
        task.update_job_progress(job_id, 30)
        
        # Convert document
        file_obj.seek(0)
        result = _convert_sync(converter, file_obj, job)
        
        task.update_job_progress(job_id, 70)
        
        # Prepare output based on format
        if job.output_format == OutputFormat.JSON:
            # Create structured JSON based on document type
            json_output = _create_structured_json(result, job.file_name)
            output_content = json.dumps(json_output, indent=2, ensure_ascii=False)
        else:  # Markdown
            output_content = result.content
        
        task.update_job_progress(job_id, 80)
        
        # Save result
        result_path = sync_storage.save_result(
            job_id,
            output_content,
            job.output_format.value
        )
        
        task.update_job_progress(job_id, 90)
        
        # Update job as completed
        sync_job_store.update(
            job_id,
            JobUpdate(
                status=JobStatus.COMPLETED,
                progress=100,
                result_path=result_path,
                completed_at=datetime.utcnow()
            )
        )
        
        # Get result URL
        result_url = sync_storage.get_result_url(job_id, job.output_format.value)
        
        # Send webhook notification
        job = sync_job_store.get(job_id)
        sync_webhook_service.notify_job_status(job, result_url)
        
        # Clean up uploaded file on successful completion
        sync_storage.delete_file(job.file_path)
        
        return {
            "job_id": job_id,
            "status": "completed",
            "result_path": result_path,
            "result_url": result_url
        }
        
    except Exception as e:
        # Update job as failed
        try:
            sync_job_store.update(
                job_id,
                JobUpdate(
                    status=JobStatus.FAILED,
                    error_message=str(e),
                    completed_at=datetime.utcnow()
                )
            )
            
            # Send webhook notification
            job = sync_job_store.get(job_id)
            sync_webhook_service.notify_job_status(job)
        except Exception as notify_error:
            print(f"Failed to update job or send notification: {notify_error}")
        
        raise ConversionException(f"Conversion failed: {str(e)}")


def _convert_sync(converter, file_obj, job):
    """Convert async converter to sync call"""
    import asyncio
    
    # Create event loop for converter
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Prepare conversion parameters
        convert_kwargs = {
            'filename': job.file_name,
            'extension': Path(job.file_name).suffix.lower(),
            'use_ocr': job.use_ocr,
            'ocr_provider': job.ocr_provider.value
        }
        
        return loop.run_until_complete(
            converter.convert(file_obj, **convert_kwargs)
        )
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def _create_structured_json(result: "ConverterResult", filename: str) -> dict:
    """Create structured JSON output based on document type and content"""
    from pathlib import Path
    
    file_extension = Path(filename).suffix.lower()
    
    # Base structure
    json_output = {
        "document": {
            "filename": filename,
            "title": result.title,
            "type": _get_document_type(file_extension),
            "metadata": result.metadata
        },
        "content": {},
        "images": {}
    }
    
    # Add images if present
    if result.images:
        json_output["images"] = {
            name: base64.b64encode(data).decode('utf-8')
            for name, data in result.images.items()
        }
    
    # Structure content based on document type
    if file_extension in {'.pdf'}:
        json_output["content"] = _structure_pdf_content(result.content)
    elif file_extension in {'.pptx', '.pptm', '.potx', '.potm'}:
        json_output["content"] = _structure_presentation_content(result.content)
    elif file_extension in {'.xlsx', '.xlsm', '.xls'}:
        json_output["content"] = _structure_spreadsheet_content(result.content, result.metadata)
    elif file_extension in {'.docx', '.rtf'}:
        json_output["content"] = _structure_document_content(result.content)
    else:
        # Default structure for other types
        json_output["content"] = {
            "type": "text",
            "text": result.content
        }
    
    return json_output


def _get_document_type(extension: str) -> str:
    """Get document type based on extension"""
    type_mapping = {
        '.pdf': 'PDF Document',
        '.docx': 'Word Document',
        '.pptx': 'PowerPoint Presentation',
        '.pptm': 'PowerPoint Presentation (Macro-enabled)',
        '.xlsx': 'Excel Workbook',
        '.xlsm': 'Excel Workbook (Macro-enabled)',
        '.xls': 'Excel Workbook (Legacy)',
        '.rtf': 'Rich Text Document',
        '.txt': 'Text Document',
        '.md': 'Markdown Document',
    }
    return type_mapping.get(extension, 'Unknown Document')


def _structure_pdf_content(content: str) -> dict:
    """Structure PDF content page-wise"""
    pages = []
    current_page = None
    current_content = []
    
    lines = content.split('\n')
    
    for line in lines:
        if line.strip().startswith('## Page '):
            # Save previous page
            if current_page is not None:
                page_text = '\n'.join(current_content).strip()
                if page_text:  # Only add pages with content
                    pages.append({
                        "page_number": current_page,
                        "text": page_text,
                        "word_count": len(page_text.split()) if page_text else 0
                    })
            
            # Start new page
            try:
                current_page = int(line.replace('## Page ', '').strip())
                current_content = []
            except ValueError:
                current_content.append(line)
        else:
            if line.strip():  # Skip empty lines
                current_content.append(line)
    
    # Add last page
    if current_page is not None:
        page_text = '\n'.join(current_content).strip()
        if page_text:
            pages.append({
                "page_number": current_page,
                "text": page_text,
                "word_count": len(page_text.split()) if page_text else 0
            })
    
    return {
        "type": "multi_page_document",
        "total_pages": len(pages),
        "pages": pages
    }


def _structure_presentation_content(content: str) -> dict:
    """Structure presentation content slide-wise"""
    slides = []
    current_slide = None
    current_content = []
    
    lines = content.split('\n')
    
    for line in lines:
        if line.strip().startswith('# Slide '):
            # Save previous slide
            if current_slide is not None:
                slide_text = '\n'.join(current_content).strip()
                if slide_text:  # Only add slides with content
                    slides.append({
                        "slide_number": current_slide,
                        "text": slide_text,
                        "summary": _extract_slide_summary(slide_text)
                    })
            
            # Start new slide
            try:
                current_slide = int(line.replace('# Slide ', '').strip())
                current_content = []
            except ValueError:
                current_content.append(line)
        else:
            if line.strip():  # Skip empty lines
                current_content.append(line)
    
    # Add last slide
    if current_slide is not None:
        slide_text = '\n'.join(current_content).strip()
        if slide_text:
            slides.append({
                "slide_number": current_slide,
                "text": slide_text,
                "summary": _extract_slide_summary(slide_text)
            })
    
    return {
        "type": "presentation",
        "total_slides": len(slides),
        "slides": slides
    }


def _structure_spreadsheet_content(content: str, metadata: dict) -> dict:
    """Structure spreadsheet content hierarchically"""
    sheets = []
    current_sheet = None
    current_table = []
    
    lines = content.split('\n')
    
    for line in lines:
        if line.strip().startswith('# Sheet: '):
            # Save previous sheet
            if current_sheet is not None:
                table_data = _parse_table_data_simple(current_table)
                sheets.append({
                    "sheet_name": current_sheet,
                    "row_count": table_data["row_count"],
                    "column_count": table_data["column_count"],
                    "headers": table_data["headers"],
                    "has_data": table_data["has_data"],
                    "sample_data": table_data["sample_data"]  # First few rows only
                })
            
            # Start new sheet
            current_sheet = line.replace('# Sheet: ', '').strip()
            current_table = []
        elif line.strip().startswith('|') and '|' in line:
            # Table row
            current_table.append(line.strip())
        elif line.strip() == "*Empty sheet*":
            if current_sheet:
                sheets.append({
                    "sheet_name": current_sheet,
                    "row_count": 0,
                    "column_count": 0,
                    "headers": [],
                    "has_data": False,
                    "sample_data": []
                })
                current_sheet = None
    
    # Add last sheet
    if current_sheet is not None:
        table_data = _parse_table_data_simple(current_table)
        sheets.append({
            "sheet_name": current_sheet,
            "row_count": table_data["row_count"],
            "column_count": table_data["column_count"],
            "headers": table_data["headers"],
            "has_data": table_data["has_data"],
            "sample_data": table_data["sample_data"]
        })
    
    return {
        "type": "spreadsheet",
        "total_sheets": len(sheets),
        "sheet_names": metadata.get('sheet_names', []),
        "sheets": sheets
    }


def _structure_document_content(content: str) -> dict:
    """Structure document content with headings and paragraphs"""
    sections = []
    current_section = None
    current_content = []
    
    lines = content.split('\n')
    
    for line in lines:
        if line.strip().startswith('#'):
            # Save previous section
            if current_section is not None:
                section_text = '\n'.join(current_content).strip()
                if section_text:
                    sections.append({
                        "heading": current_section,
                        "text": section_text,
                        "word_count": len(section_text.split()) if section_text else 0
                    })
            
            # Start new section
            current_section = line.strip().lstrip('#').strip()
            current_content = []
        else:
            if line.strip():
                current_content.append(line)
    
    # Add last section
    if current_section is not None:
        section_text = '\n'.join(current_content).strip()
        if section_text:
            sections.append({
                "heading": current_section,
                "text": section_text,
                "word_count": len(section_text.split()) if section_text else 0
            })
    
    # If no sections found, treat as single content block
    if not sections and content.strip():
        sections.append({
            "heading": "Document Content",
            "text": content.strip(),
            "word_count": len(content.split()) if content else 0
        })
    
    return {
        "type": "structured_document",
        "total_sections": len(sections),
        "sections": sections
    }


def _extract_slide_summary(slide_text: str) -> str:
    """Extract a brief summary from slide text"""
    lines = slide_text.split('\n')
    
    # Look for heading (starts with ##)
    for line in lines:
        line = line.strip()
        if line.startswith('##'):
            return line.lstrip('#').strip()
    
    # If no heading, return first non-empty line (truncated)
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            return line[:100] + "..." if len(line) > 100 else line
    
    return "No content"


def _parse_table_data_simple(table_lines: list) -> dict:
    """Parse markdown table into simple summary data"""
    if not table_lines:
        return {
            "row_count": 0,
            "column_count": 0,
            "headers": [],
            "has_data": False,
            "sample_data": []
        }
    
    # Remove separator lines (lines with only -, |, and spaces)
    data_lines = [line for line in table_lines if not all(c in '-| ' for c in line)]
    
    if not data_lines:
        return {
            "row_count": 0,
            "column_count": 0,
            "headers": [],
            "has_data": False,
            "sample_data": []
        }
    
    # Get headers from first line
    headers = []
    sample_data = []
    
    for i, line in enumerate(data_lines[:6]):  # Only process first 6 rows max
        cells = [cell.strip() for cell in line.split('|')[1:-1]]
        
        if i == 0:
            headers = cells
        else:
            # Only keep first 3 sample rows
            if len(sample_data) < 3:
                sample_data.append(cells)
    
    return {
        "row_count": len(data_lines) - 1,  # Exclude header
        "column_count": len(headers),
        "headers": headers,
        "has_data": len(data_lines) > 1,
        "sample_data": sample_data
    }