from celery import Celery

from ..core.config import settings


# Create Celery app
celery_app = Celery(
    settings.app_name,
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=['src.services.tasks']
)

# Configure Celery with async support
celery_app.conf.update(
    task_serializer=settings.celery_task_serializer,
    accept_content=settings.celery_accept_content,
    result_serializer=settings.celery_result_serializer,
    timezone=settings.celery_timezone,
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    # Enable async task support
    task_always_eager=False,
    task_eager_propagates=True,
    # Worker configuration for Windows compatibility
    worker_pool='solo',  # Use solo for Windows compatibility
)