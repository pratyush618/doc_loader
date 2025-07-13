# JSON Output Format

When choosing JSON as the output format, the document converter provides structured, hierarchical data that preserves the organization and meaning of the original document.

## Base Structure

All JSON outputs follow this base structure:

```json
{
  "document": {
    "filename": "original_filename.ext",
    "title": "Document Title",
    "type": "Document Type",
    "metadata": { /* document-specific metadata */ }
  },
  "content": { /* structured content based on document type */ },
  "images": { /* base64-encoded images if present */ }
}
```

## Document-Specific Structures

### PDF Documents (Multi-page)

PDF documents are structured page-wise with concise summaries:

```json
{
  "document": {
    "filename": "report.pdf",
    "title": "Annual Report",
    "type": "PDF Document",
    "metadata": {
      "num_pages": 10,
      "author": "John Doe",
      "created": "2024-01-15T10:30:00Z"
    }
  },
  "content": {
    "type": "multi_page_document",
    "total_pages": 10,
    "pages": [
      {
        "page_number": 1,
        "text": "Page 1 complete text content...",
        "word_count": 245
      },
      {
        "page_number": 2,
        "text": "Page 2 complete text content...",
        "word_count": 312
      }
    ]
  }
}
```

### PowerPoint Presentations (Slide-wise)

Presentations are structured slide-wise with concise summaries:

```json
{
  "document": {
    "filename": "presentation.pptx",
    "title": "Marketing Strategy",
    "type": "PowerPoint Presentation",
    "metadata": {
      "num_slides": 15,
      "slide_width": 9144000,
      "slide_height": 6858000
    }
  },
  "content": {
    "type": "presentation",
    "total_slides": 15,
    "slides": [
      {
        "slide_number": 1,
        "text": "## Introduction\n- Point 1\n- Point 2\n- Point 3",
        "summary": "Introduction"
      },
      {
        "slide_number": 2,
        "text": "## Market Analysis\n- Current trends\n- Competition overview",
        "summary": "Market Analysis"
      }
    ]
  }
}
```

### Excel Spreadsheets (Hierarchical Structure)

Spreadsheets provide summary information with sample data (not full data):

```json
{
  "document": {
    "filename": "data.xlsx",
    "title": "Sales Data",
    "type": "Excel Workbook",
    "metadata": {
      "num_sheets": 3,
      "sheet_names": ["Sales", "Summary", "Charts"]
    }
  },
  "content": {
    "type": "spreadsheet",
    "total_sheets": 3,
    "sheet_names": ["Sales", "Summary", "Charts"],
    "sheets": [
      {
        "sheet_name": "Sales",
        "row_count": 1000,
        "column_count": 5,
        "headers": ["Date", "Product", "Amount", "Region", "Salesperson"],
        "has_data": true,
        "sample_data": [
          ["2024-01-01", "Widget A", "150.00", "North", "John"],
          ["2024-01-02", "Widget B", "200.00", "South", "Jane"],
          ["2024-01-03", "Widget C", "175.00", "East", "Bob"]
        ]
      },
      {
        "sheet_name": "Summary",
        "row_count": 12,
        "column_count": 3,
        "headers": ["Month", "Total Sales", "Units Sold"],
        "has_data": true,
        "sample_data": [
          ["January", "50000", "250"],
          ["February", "48000", "240"]
        ]
      }
    ]
  }
}
```

### Word Documents (Section-based)

Word documents are organized by sections and headings:

```json
{
  "document": {
    "filename": "report.docx",
    "title": "Project Report",
    "type": "Word Document",
    "metadata": {
      "author": "Jane Smith",
      "created": "2024-01-10T14:30:00Z",
      "num_paragraphs": 25
    }
  },
  "content": {
    "type": "structured_document",
    "total_sections": 5,
    "sections": [
      {
        "heading": "Executive Summary",
        "content": "This section contains the executive summary..."
      },
      {
        "heading": "Introduction",
        "content": "The introduction section explains..."
      }
    ]
  }
}
```

### Images

When documents contain images, they are included as base64-encoded data:

```json
{
  "images": {
    "chart1.png": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
    "logo.jpg": "base64_encoded_image_data_here..."
  }
}
```

## Element Types

### Slide Elements (PowerPoint)

- **heading**: Text with heading formatting
- **bullet_point**: List items and bullet points
- **text**: Regular text content
- **table_row**: Table row data

### Table Data (Spreadsheets)

- **header**: Table header row
- **data**: Data rows with both cell arrays and key-value mapping
- **empty**: Empty sheets or tables

## Usage Examples

### Accessing Page Content (PDF)
```javascript
// Get content from page 5
const page5Content = jsonData.content.pages.find(p => p.page_number === 5).content;
```

### Accessing Slide Data (PowerPoint)
```javascript
// Get all bullet points from slide 3
const slide3 = jsonData.content.slides.find(s => s.slide_number === 3);
const bulletPoints = slide3.elements.filter(e => e.type === 'bullet_point');
```

### Accessing Sheet Data (Excel)
```javascript
// Get data from "Sales" sheet
const salesSheet = jsonData.content.sheets.find(s => s.sheet_name === 'Sales');
const salesData = salesSheet.data.rows.filter(r => r.type === 'data');

// Access specific cell data
salesData.forEach(row => {
  console.log(`Product: ${row.data.Product}, Amount: ${row.data.Amount}`);
});
```

### Accessing Document Sections (Word)
```javascript
// Get introduction section
const intro = jsonData.content.sections.find(s => s.heading === 'Introduction');
console.log(intro.content);
```

This structured approach makes it easy to programmatically process documents while preserving their original organization and hierarchy.