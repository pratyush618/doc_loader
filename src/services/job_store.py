from typing import Optional, Dict
from datetime import datetime
import redis.asyncio as redis

from ..core.config import settings
from ..core.exceptions import JobNotFoundException
from ..models.job import Job, JobUpdate


class JobStore:
    """Redis-based job storage"""
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.prefix = "doc_converter:job:"
        self.ttl = 86400  # 24 hours
    
    async def connect(self):
        """Connect to Redis with connection pooling"""
        if not self.redis:
            # Create connection pool for better async handling
            connection_pool = redis.ConnectionPool.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True
            )
            self.redis = redis.Redis(connection_pool=connection_pool)
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            self.redis = None
    
    async def create(self, job: Job) -> Job:
        """Create a new job"""
        await self.connect()
        
        # Serialize job
        job_data = job.model_dump_json()
        
        # Store in Redis with TTL
        key = f"{self.prefix}{job.id}"
        await self.redis.set(key, job_data, ex=self.ttl)
        
        return job
    
    async def get(self, job_id: str) -> Job:
        """Get job by ID"""
        await self.connect()
        
        key = f"{self.prefix}{job_id}"
        job_data = await self.redis.get(key)
        
        if not job_data:
            raise JobNotFoundException(job_id)
        
        return Job.model_validate_json(job_data)
    
    async def update(self, job_id: str, update: JobUpdate) -> Job:
        """Update job"""
        # Get existing job
        job = await self.get(job_id)
        
        # Update fields
        update_data = update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(job, field, value)
        
        # Update timestamp
        job.updated_at = datetime.utcnow()
        
        # Save back to Redis
        await self.connect()
        key = f"{self.prefix}{job_id}"
        await self.redis.set(key, job.model_dump_json(), ex=self.ttl)
        
        return job
    
    async def delete(self, job_id: str) -> None:
        """Delete job"""
        await self.connect()
        
        key = f"{self.prefix}{job_id}"
        await self.redis.delete(key)
    
    async def exists(self, job_id: str) -> bool:
        """Check if job exists"""
        await self.connect()
        
        key = f"{self.prefix}{job_id}"
        return await self.redis.exists(key) > 0
    
    async def get_all_jobs(self, pattern: Optional[str] = None) -> Dict[str, Job]:
        """Get all jobs matching pattern"""
        await self.connect()
        
        # Get all keys
        search_pattern = f"{self.prefix}{pattern or '*'}"
        keys = []
        async for key in self.redis.scan_iter(match=search_pattern):
            keys.append(key)
        
        if not keys:
            return {}
        
        # Get all values
        values = await self.redis.mget(keys)
        
        # Parse jobs
        jobs = {}
        for key, value in zip(keys, values):
            if value:
                job_id = key.replace(self.prefix, "")
                jobs[job_id] = Job.model_validate_json(value)
        
        return jobs


# Global instance
job_store = JobStore()