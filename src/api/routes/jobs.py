import uuid
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import FileResponse

from ...core.exceptions import JobNotFoundException, FileSizeException
from ...models.job import Job, JobResponse, OutputFormat, OCRProvider
from ...services.sync_storage import sync_storage
from ...services.sync_job_store import sync_job_store
from ...services.tasks import convert_document


router = APIRouter()


@router.post("/", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    file: UploadFile = File(...),
    output_format: OutputFormat = Form(OutputFormat.MARKDOWN),
    webhook_url: Optional[str] = Form(None),
    use_ocr: bool = Form(False),
    ocr_provider: OCRProvider = Form(OCRProvider.EASY_OCR),
) -> JobResponse:
    """
    Create a new document conversion job.
    
    Args:
        file: File to convert
        output_format: Output format (md or json)
        webhook_url: Optional webhook URL for notifications
        use_ocr: Whether to use OCR for image text extraction
        ocr_provider: OCR provider to use (paddle or mistral)
        
    Returns:
        Job details with ID for tracking
    """
    try:
        # Read file content
        content = await file.read()
        
        # Save uploaded file
        file_path = sync_storage.save_upload(content, file.filename)
        
        # Create job
        job = Job(
            id=str(uuid.uuid4()),
            file_name=file.filename,
            file_path=file_path,
            output_format=output_format,
            webhook_url=webhook_url,
            use_ocr=use_ocr,
            ocr_provider=ocr_provider,
        )
        
        # Store job
        sync_job_store.create(job)
        
        # Queue conversion task
        convert_document.delay(job.id)
        
        # Return job response
        return JobResponse(
            id=job.id,
            status=job.status,
            progress=job.progress,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
        
    except FileSizeException as e:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create job: {str(e)}"
        )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str) -> JobResponse:
    """
    Get job status by ID.
    
    Args:
        job_id: Job ID
        
    Returns:
        Job status and details
    """
    try:
        job = sync_job_store.get(job_id)
        
        # Build response
        response = JobResponse(
            id=job.id,
            status=job.status,
            progress=job.progress,
            created_at=job.created_at,
            updated_at=job.updated_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
        )
        
        # Add result URL if completed
        if job.status == "completed" and job.result_path:
            response.result_url = sync_storage.get_result_url(job.id, job.output_format.value)
        
        return response
        
    except JobNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )


@router.get("/{job_id}/result")
async def download_result(job_id: str):
    """
    Download conversion result.
    
    Args:
        job_id: Job ID
        
    Returns:
        File download response
    """
    try:
        # Get job
        job = sync_job_store.get(job_id)
        
        # Check if completed
        if job.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job {job_id} is not completed yet"
            )
        
        # Check if result exists
        if not job.result_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Result not found for job {job_id}"
            )
        
        # Check if file exists
        result_path = Path(job.result_path)
        if not result_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Result file not found"
            )
        
        # Determine media type
        media_type = "application/json" if job.output_format == OutputFormat.JSON else "text/markdown"
        
        # Generate proper filename by removing original extension
        base_name = Path(job.file_name).stem  # Gets filename without extension
        output_filename = f"{base_name}.{job.output_format.value}"
        
        # Return file
        return FileResponse(
            path=result_path,
            media_type=media_type,
            filename=output_filename
        )
        
    except JobNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download result: {str(e)}"
        )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_job(job_id: str):
    """
    Cancel a job and clean up resources.
    
    Args:
        job_id: Job ID
    """
    try:
        # Get job
        job = sync_job_store.get(job_id)
        
        # Clean up files
        sync_storage.delete_file(job.file_path)
        if job.result_path:
            sync_storage.delete_file(job.result_path)
        
        # Delete job
        sync_job_store.delete(job_id)
        
    except JobNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {str(e)}"
        )