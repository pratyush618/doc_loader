import httpx
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential

from ..core.config import settings
from ..core.exceptions import WebhookException
from ..models.job import Job, JobStatus


class SyncWebhookService:
    """Synchronous webhook service"""
    
    def __init__(self):
        self.timeout = settings.webhook_timeout
        self.max_retries = settings.webhook_max_retries
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def send_notification(self, webhook_url: str, job: Job, 
                         result_url: Optional[str] = None) -> None:
        """
        Send webhook notification about job status.
        
        Args:
            webhook_url: URL to send notification to
            job: Job object
            result_url: URL to download result (if completed)
            
        Raises:
            WebhookException: If notification fails after retries
        """
        # Prepare payload
        payload = {
            "job_id": job.id,
            "status": job.status,
            "progress": job.progress,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "metadata": job.metadata,
        }
        
        # Add completion-specific fields
        if job.status == JobStatus.COMPLETED:
            payload["completed_at"] = job.completed_at.isoformat() if job.completed_at else None
            payload["result_url"] = result_url
        elif job.status == JobStatus.FAILED:
            payload["error_message"] = job.error_message
        
        # Send webhook
        try:
            with httpx.Client() as client:
                response = client.post(
                    webhook_url,
                    json=payload,
                    timeout=self.timeout,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": f"{settings.app_name}/1.0"
                    }
                )
                
                # Check response
                if response.status_code >= 400:
                    raise WebhookException(
                        f"Webhook returned status {response.status_code}: {response.text}"
                    )
                    
        except httpx.TimeoutException:
            raise WebhookException(f"Webhook timeout after {self.timeout}s")
        except httpx.RequestError as e:
            raise WebhookException(f"Webhook request failed: {str(e)}")
    
    def notify_job_status(self, job: Job, result_url: Optional[str] = None) -> None:
        """
        Send webhook notification if configured.
        
        Args:
            job: Job object
            result_url: URL to download result (if completed)
        """
        # Determine webhook URL
        webhook_url = job.webhook_url or settings.default_webhook_url
        
        if not webhook_url:
            return  # No webhook configured
        
        try:
            self.send_notification(webhook_url, job, result_url)
        except Exception as e:
            # Log error but don't fail the job
            print(f"Webhook notification failed: {str(e)}")


# Global sync instance
sync_webhook_service = SyncWebhookService()