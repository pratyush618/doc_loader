from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Application Settings
    app_name: str = Field(default="doc-converter", env="APP_NAME")
    app_env: str = Field(default="production", env="APP_ENV")
    debug: bool = Field(default=False, env="DEBUG")
    
    # API Settings
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Celery Configuration
    celery_broker_url: str = Field(default="redis://localhost:6379/0", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/0", env="CELERY_RESULT_BACKEND")
    celery_task_serializer: str = Field(default="json", env="CELERY_TASK_SERIALIZER")
    celery_result_serializer: str = Field(default="json", env="CELERY_RESULT_SERIALIZER")
    celery_accept_content: List[str] = Field(default=["json"], env="CELERY_ACCEPT_CONTENT")
    celery_timezone: str = Field(default="UTC", env="CELERY_TIMEZONE")
    
    # Storage Settings
    upload_dir: str = Field(default="./uploads", env="UPLOAD_DIR")
    output_dir: str = Field(default="./outputs", env="OUTPUT_DIR")
    max_file_size: int = Field(default=104857600, env="MAX_FILE_SIZE")  # 100MB
    file_ttl_hours: int = Field(default=24, env="FILE_TTL_HOURS")  # TTL for temp files
    
    # Webhook Settings
    default_webhook_url: Optional[str] = Field(default=None, env="DEFAULT_WEBHOOK_URL")
    webhook_timeout: int = Field(default=30, env="WEBHOOK_TIMEOUT")
    webhook_max_retries: int = Field(default=3, env="WEBHOOK_MAX_RETRIES")
    
    # Security Settings
    secret_key: str = Field(default="your-secret-key-here", env="SECRET_KEY")
    allowed_origins: str = Field(default="*", env="ALLOWED_ORIGINS")
    
    # Image Processing
    image_compression_quality: int = Field(default=95, env="IMAGE_COMPRESSION_QUALITY")
    image_max_width: int = Field(default=2048, env="IMAGE_MAX_WIDTH")
    image_max_height: int = Field(default=2048, env="IMAGE_MAX_HEIGHT")
    
    # OCR Settings (existing)
    mistral_api_key: Optional[str] = Field(default=None, env="MISTRAL_API_KEY")
    mistral_api_url: str = Field(default="https://api.mistral.ai/v1/chat/completions", env="MISTRAL_API_URL")
    mistral_model: str = Field(default="pixtral-12b-2409", env="MISTRAL_MODEL")
    paddle_ocr_use_gpu: bool = Field(default=False, env="PADDLE_OCR_USE_GPU")
    paddle_ocr_lang: str = Field(default="en", env="PADDLE_OCR_LANG")
    paddle_models_dir: str = Field(default="./models/paddle_models", env="PADDLE_MODELS_DIR")
    
    # EasyOCR Settings (SIMPLER VERSION)
    easy_ocr_use_gpu: bool = Field(default=False, env="EASY_OCR_USE_GPU")
    easy_ocr_lang: str = Field(default="en", env="EASY_OCR_LANG")  # Keep as string
    easy_ocr_model_storage: str = Field(default="./models/easy_ocr_models", env="EASY_OCR_MODEL_STORAGE")
    easy_ocr_text_threshold: float = Field(default=0.7, env="EASY_OCR_TEXT_THRESHOLD")
    easy_ocr_link_threshold: float = Field(default=0.4, env="EASY_OCR_LINK_THRESHOLD")
    easy_ocr_low_text: float = Field(default=0.4, env="EASY_OCR_LOW_TEXT")
    
    @property
    def easy_ocr_lang_list(self) -> List[str]:
        """Parse comma-separated languages into a list"""
        return [lang.strip() for lang in self.easy_ocr_lang.split(",") if lang.strip()]
    
    # PaddlePaddle Environment Settings
    flags_use_mkldnn: str = Field(default="0", env="FLAGS_USE_MKLDNN")
    flags_enable_eager_mode: str = Field(default="1", env="FLAGS_ENABLE_EAGER_MODE")
    paddle_log_level: str = Field(default="3", env="PADDLE_LOG_LEVEL")
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse allowed_origins string into a list"""
        if self.allowed_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    @field_validator("celery_accept_content", mode="before")
    @classmethod
    def parse_accept_content(cls, v):
        if isinstance(v, str):
            return [content.strip() for content in v.split(",")]
        return v


settings = Settings()