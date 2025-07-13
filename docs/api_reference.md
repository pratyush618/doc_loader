# API Reference

## File Download Behavior

When downloading converted files via the `/api/v1/jobs/{job_id}/result` endpoint, the filename is automatically generated based on the original filename and output format:

### Filename Generation Rules

1. **Original extension is removed**: The file extension from the uploaded file is stripped
2. **New extension is added**: The appropriate extension for the output format is added
3. **Base name is preserved**: The original filename (without extension) is kept intact

### Examples

| Original Filename | Output Format | Download Filename |
|------------------|---------------|------------------|
| `document.pdf` | `md` | `document.md` |
| `presentation.pptx` | `md` | `presentation.md` |
| `spreadsheet.xlsx` | `json` | `spreadsheet.json` |
| `My Report (v2).docx` | `md` | `My Report (v2).md` |
| `data-2024.csv` | `json` | `data-2024.json` |

### Supported Output Formats

- **Markdown (`.md`)**: Human-readable markdown with embedded images as base64
- **JSON (`.json`)**: Structured data with content, metadata, and base64-encoded images

### Response Headers

The download response includes appropriate headers:

- **Content-Type**: 
  - `text/markdown` for `.md` files
  - `application/json` for `.json` files
- **Content-Disposition**: `attachment; filename="generated_filename"`

### Error Cases

- **404 Not Found**: Job doesn't exist or result file is missing
- **400 Bad Request**: Job is not completed yet
- **500 Internal Server Error**: File system or processing error

## Example Usage

```bash
# Upload file
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -F "file=@presentation.pptx" \
  -F "output_format=md"

# Response: {"id": "job_123", "status": "pending", ...}

# Check status
curl "http://localhost:8000/api/v1/jobs/job_123"

# Download result (filename will be "presentation.md")
curl "http://localhost:8000/api/v1/jobs/job_123/result" -o result.md
```