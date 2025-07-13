from typing import Optional
from datetime import datetime
import redis

from ..core.config import settings
from ..core.exceptions import JobNotFoundException
from ..models.job import Job, JobUpdate


class SyncJobStore:
    """Synchronous Redis-based job storage"""
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.prefix = "doc_converter:job:"
        self.ttl = 86400  # 24 hours
    
    def connect(self):
        """Connect to Redis"""
        if not self.redis:
            self.redis = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
    
    def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            self.redis.close()
            self.redis = None
    
    def create(self, job: Job) -> Job:
        """Create a new job"""
        self.connect()
        
        # Serialize job
        job_data = job.model_dump_json()
        
        # Store in Redis with TTL
        key = f"{self.prefix}{job.id}"
        self.redis.set(key, job_data, ex=self.ttl)
        
        return job
    
    def get(self, job_id: str) -> Job:
        """Get job by ID"""
        self.connect()
        
        key = f"{self.prefix}{job_id}"
        job_data = self.redis.get(key)
        
        if not job_data:
            raise JobNotFoundException(job_id)
        
        return Job.model_validate_json(job_data)
    
    def update(self, job_id: str, update: JobUpdate) -> Job:
        """Update job"""
        # Get existing job
        job = self.get(job_id)
        
        # Update fields
        update_data = update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(job, field, value)
        
        # Update timestamp
        job.updated_at = datetime.utcnow()
        
        # Save back to Redis
        self.connect()
        key = f"{self.prefix}{job_id}"
        self.redis.set(key, job.model_dump_json(), ex=self.ttl)
        
        return job
    
    def delete(self, job_id: str) -> None:
        """Delete job"""
        self.connect()
        
        key = f"{self.prefix}{job_id}"
        self.redis.delete(key)
    
    def exists(self, job_id: str) -> bool:
        """Check if job exists"""
        self.connect()
        
        key = f"{self.prefix}{job_id}"
        return self.redis.exists(key) > 0


# Global sync instance
sync_job_store = SyncJobStore()