# OCR Capabilities Documentation

The document converter now supports OCR (Optical Character Recognition) functionality to extract text from images within documents. This feature is especially useful for processing scanned documents, images with text, and ensuring agents can properly handle informative images.

## Supported OCR Providers

### 1. PaddleOCR (Default)
- **Provider**: `paddle`
- **Description**: Open-source OCR toolkit by PaddlePaddle
- **Languages**: Supports multiple languages (configurable)
- **Performance**: Fast and reliable for most use cases
- **Requirements**: No API key needed

### 2. Mistral AI (Premium)
- **Provider**: `mistral`
- **Description**: AI-powered OCR using Mistral's vision model
- **Languages**: Supports multiple languages
- **Performance**: High accuracy, especially for complex layouts
- **Requirements**: Mistral API key required

## Configuration

### Environment Variables

Add these variables to your `.env` file:

```bash
# OCR Settings
# Mistral AI API key for OCR (required for Mistral OCR provider)
MISTRAL_API_KEY=your_mistral_api_key_here
MISTRAL_API_URL=https://api.mistral.ai/v1/chat/completions
MISTRAL_MODEL=pixtral-12b-2409

# PaddleOCR Settings
PADDLE_OCR_USE_GPU=false
PADDLE_OCR_LANG=en
```

### Supported Languages (PaddleOCR)
- `en` - English (default)
- `ch` - Chinese
- `fr` - French
- `de` - German
- `ko` - Korean
- `ja` - Japanese
- And many more...

## API Usage

### Creating a Job with OCR

**Endpoint**: `POST /api/v1/jobs/`

**Parameters**:
- `file` - The document/image file to process
- `output_format` - Output format (`md` or `json`)
- `use_ocr` - Boolean flag to enable OCR (default: `false`)
- `ocr_provider` - OCR provider to use (`paddle` or `mistral`, default: `paddle`)
- `webhook_url` - Optional webhook URL for notifications

### Example: Using PaddleOCR

```bash
curl -X POST "http://localhost:8000/api/v1/jobs/" \
  -F "file=@document_with_images.pdf" \
  -F "output_format=md" \
  -F "use_ocr=true" \
  -F "ocr_provider=paddle"
```

### Example: Using Mistral AI OCR

```bash
curl -X POST "http://localhost:8000/api/v1/jobs/" \
  -F "file=@scanned_document.jpg" \
  -F "output_format=json" \
  -F "use_ocr=true" \
  -F "ocr_provider=mistral"
```

### Python Client Example

```python
import requests

# Upload a file with OCR processing
files = {'file': open('document.png', 'rb')}
data = {
    'output_format': 'md',
    'use_ocr': True,
    'ocr_provider': 'paddle'
}

response = requests.post('http://localhost:8000/api/v1/jobs/', files=files, data=data)
job = response.json()
print(f"Job ID: {job['id']}")
```

## Output Format

### Markdown Output
When OCR is enabled, the markdown output includes:
```markdown
# Image: filename.png

## Extracted Text (OCR)
**Provider**: paddle
**Confidence**: 0.95

**Text Content**:
```
This is the extracted text from the image...
```

## Metadata
- **format**: PNG
- **size**: [800, 600]
...
```

### JSON Output
When OCR is enabled, the JSON output includes OCR metadata:
```json
{
  "document": {
    "filename": "image.png",
    "type": "Image Document",
    "metadata": {
      "format": "PNG",
      "size": [800, 600],
      "ocr": {
        "provider": "paddle",
        "confidence": 0.95,
        "text_length": 150,
        "metadata": {
          "provider": "paddle",
          "language": "en",
          "lines_detected": 5
        }
      }
    }
  },
  "content": {
    "type": "image_with_text",
    "extracted_text": "Text extracted from image...",
    "ocr_confidence": 0.95
  }
}
```

## Use Cases

### 1. Agent Processing
When building AI agents that need to understand document content:
```python
# Enable OCR to ensure images with text are processed
job_data = {
    'use_ocr': True,
    'ocr_provider': 'mistral',  # Higher accuracy for agents
    'output_format': 'json'     # Structured data for agents
}
```

### 2. Scanned Document Processing
For processing scanned PDFs and images:
```python
job_data = {
    'use_ocr': True,
    'ocr_provider': 'paddle',   # Fast processing
    'output_format': 'md'       # Human-readable output
}
```

### 3. Multilingual Documents
For documents in different languages:
```bash
# Set language in environment
PADDLE_OCR_LANG=ch  # For Chinese documents
```

## Error Handling

The OCR service includes robust error handling:

1. **Provider Not Available**: Falls back gracefully with error message
2. **No Text Detected**: Returns empty text with appropriate metadata
3. **API Errors**: Detailed error messages for debugging
4. **Invalid Images**: Proper error handling for corrupted files

## Performance Considerations

### PaddleOCR
- **Initialization**: Downloads models on first use (~200MB)
- **Processing**: 1-3 seconds per image
- **Memory**: ~1GB RAM for models
- **GPU**: Optional GPU acceleration available

### Mistral AI
- **API Calls**: Requires internet connection
- **Rate Limits**: Subject to Mistral API limits
- **Cost**: Usage-based pricing
- **Accuracy**: Higher accuracy for complex layouts

## Best Practices

1. **Choose the Right Provider**:
   - Use PaddleOCR for fast, offline processing
   - Use Mistral AI for high-accuracy requirements

2. **Image Quality**:
   - Higher resolution images yield better OCR results
   - Ensure good contrast between text and background

3. **Language Configuration**:
   - Set the correct language for PaddleOCR
   - Mistral AI automatically detects language

4. **Resource Management**:
   - PaddleOCR models are cached after first load
   - Consider memory usage for high-volume processing

## Troubleshooting

### Common Issues

1. **PaddleOCR Not Available**:
   ```
   Solution: Install dependencies with `uv sync`
   ```

2. **Mistral API Errors**:
   ```
   Solution: Check API key in .env file
   ```

3. **Poor OCR Results**:
   ```
   Solution: Check image quality, try different provider
   ```

4. **Memory Issues**:
   ```
   Solution: Restart service to clear model cache
   ```

5. **PaddleOCR MKLDNN Warnings**:
   ```
   Solution: Warnings are automatically suppressed by paddle_config.py
   Set environment variables in .env to control behavior
   ```

### Warning Suppression

The application automatically suppresses PaddleOCR warnings including:
- MKLDNN compatibility warnings
- Model download messages
- GPU/CPU optimization notices

This is configured in `src/core/paddle_config.py` and applied automatically.

### Debugging

Enable debug logging to troubleshoot OCR issues:
```bash
DEBUG=true
```

Check OCR provider availability:
```python
from src.services.ocr_service import ocr_service
print(ocr_service.get_available_providers())
```

### Environment Variables for PaddleOCR

Advanced users can control PaddleOCR behavior via environment variables:
```bash
# Disable MKLDNN (already set by default)
FLAGS_use_mkldnn=0

# Control logging level (3=errors only)
PADDLE_LOG_LEVEL=3

# Enable eager mode for better performance
FLAGS_enable_eager_mode=1
```