# Document Converter API

A production-ready document converter application that transforms various document formats into Markdown or JSON with async processing, event queues, and webhook notifications.

## Features

- **Multi-format Support**: Converts PDF, DOCX, images, text files, and more
- **Async Processing**: Event queue-based processing using Celery and Redis
- **Image Handling**: Base64 encoding with lossless compression for images
- **Webhook Notifications**: Real-time status updates via webhooks
- **REST API**: FastAPI-based API with OpenAPI documentation
- **Production Ready**: Docker support, health checks, and proper error handling

## Supported Formats

### Input Formats
- **Documents**: PDF, Microsoft Word (.docx), Rich Text Format (.rtf)
- **Presentations**: Microsoft PowerPoint (.pptx, .pptm, .potx, .potm)
- **Spreadsheets**: Microsoft Excel (.xlsx, .xlsm, .xls)
- **Images**: PNG, JPEG, GIF, BMP, WebP, ICO, TIFF
- **Text**: Plain text (.txt), Markdown (.md), Log files
- **Other**: HTML, CSV, JSON, XML

### Output Formats
- **Markdown (.md)**: Human-readable markdown with embedded base64 images
- **Structured JSON (.json)**: Hierarchical data preserving document organization:
  - **PDF**: Page-wise content structure
  - **PowerPoint**: Slide-wise with element-level parsing
  - **Excel**: Sheet-based hierarchical organization with table data
  - **Word**: Section-based structure with headings and content
  - **Images**: Base64-encoded image data included

## Quick Start

### Using Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd doc_converter
```

2. Copy environment variables:
```bash
cp .env.example .env
```

3. Start the services:
```bash
docker-compose up -d
```

4. The API will be available at `http://localhost:8000`
5. API documentation at `http://localhost:8000/docs`

### Development Setup with uv (Recommended for Development)

This project uses [uv](https://docs.astral.sh/uv/) for fast Python package management.

1. Install uv:
```bash
# Windows (using winget)
winget install --id=astral-sh.uv -e

# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Using pip (any platform)
pip install uv
```

2. Clone and setup:
```bash
git clone <repository-url>
cd doc_converter
uv sync  # Creates .venv and installs dependencies
```

3. Start Redis:
```bash
redis-server
```

4. Start the API server:
```bash
uv run python run_api.py
```

5. Start the Celery worker:
```bash
uv run python run_worker.py
```

### Manual Installation (Alternative)

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Follow steps 3-5 above, replacing `uv run` with direct Python commands.

## API Usage

### Submit a Document for Conversion

```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf" \
  -F "output_format=md" \
  -F "webhook_url=https://your-webhook-url.com/callback"
```

Response:
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "progress": 0,
  "created_at": "2023-12-01T10:00:00Z",
  "updated_at": "2023-12-01T10:00:00Z"
}
```

### Check Job Status

```bash
curl "http://localhost:8000/api/v1/jobs/123e4567-e89b-12d3-a456-426614174000"
```

### Download Result

```bash
curl "http://localhost:8000/api/v1/jobs/123e4567-e89b-12d3-a456-426614174000/result" \
  -o converted_document.md
```

## Webhook Notifications

When a job completes (successfully or with failure), a webhook notification is sent:

```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "progress": 100,
  "created_at": "2023-12-01T10:00:00Z",
  "updated_at": "2023-12-01T10:05:00Z",
  "completed_at": "2023-12-01T10:05:00Z",
  "result_url": "http://localhost:8000/api/v1/jobs/123e4567-e89b-12d3-a456-426614174000/result",
  "metadata": {}
}
```

## Configuration

Environment variables (see `.env.example`):

- `REDIS_URL`: Redis connection URL
- `MAX_FILE_SIZE`: Maximum upload file size (bytes)
- `DEFAULT_WEBHOOK_URL`: Default webhook URL if not provided
- `IMAGE_COMPRESSION_QUALITY`: Image compression quality (1-100)
- `UPLOAD_DIR`: Directory for uploaded files
- `OUTPUT_DIR`: Directory for converted files

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   FastAPI   │    │    Redis    │    │   Celery    │
│   Server    │◄──►│   Queue     │◄──►│   Worker    │
└─────────────┘    └─────────────┘    └─────────────┘
       │                                      │
       ▼                                      ▼
┌─────────────┐                      ┌─────────────┐
│  File       │                      │  Document   │
│  Storage    │                      │  Converters │
└─────────────┘                      └─────────────┘
       │                                      │
       ▼                                      ▼
┌─────────────┐                      ┌─────────────┐
│  Webhook    │                      │  Image      │
│  Service    │                      │  Processing │
└─────────────┘                      └─────────────┘
```

## Development

### Running Tests

With uv:
```bash
uv run pytest tests/ -v
uv run pytest --cov=src tests/  # With coverage
```

Traditional:
```bash
pytest tests/ -v
```

### Code Quality

With uv:
```bash
# Format code
uv run black src/ tests/

# Lint code
uv run flake8 src/ tests/

# Type checking
uv run mypy src/
```

Traditional:
```bash
black src/ tests/
flake8 src/ tests/
mypy src/
```

### Adding Dependencies

With uv:
```bash
# Add runtime dependency
uv add package-name

# Add development dependency
uv add --dev pytest-package

# Update dependencies
uv lock --upgrade && uv sync
```

## Production Deployment

1. Set up environment variables
2. Configure Redis for persistence
3. Set up monitoring (health endpoints available)
4. Configure webhook endpoint security
5. Set up file storage with proper permissions
6. Configure load balancing for multiple workers

## License

MIT License