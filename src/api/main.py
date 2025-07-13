from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Configure PaddlePaddle early to suppress warnings
from ..core.paddle_config import suppress_paddle_logs
suppress_paddle_logs()

from ..core.config import settings
from ..services.job_store import job_store
from .routes import jobs, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    await job_store.connect()
    yield
    # Shutdown
    await job_store.disconnect()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Production-ready document converter with async processing",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    jobs.router,
    prefix=f"{settings.api_prefix}/jobs",
    tags=["jobs"]
)

app.include_router(
    health.router,
    prefix=settings.api_prefix,
    tags=["health"]
)