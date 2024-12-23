# Research Assistant

A tool for managing academic research materials, including PDF processing, knowledge ingestion, and semantic search capabilities using AI agents.

## Quick Start (Simplified Setup)

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Convert PDFs:
```bash
# To Markdown
python scripts/pdf_to_markdown.py sources_pdf/your-file.pdf -o sources_markdown/your-file.md

# To PNG images (300 DPI)
python scripts/pdf_to_png.py sources_pdf/your-file.pdf -o sources_png/your-file/

# Convert all PDFs in the directory
for pdf in sources_pdf/*.pdf; do
    filename=$(basename "$pdf" .pdf)
    python scripts/pdf_to_markdown.py "$pdf" -o "sources_markdown/$filename.md"
    python scripts/pdf_to_png.py "$pdf" -o "sources_png/$filename"
done
```

## Project Structure

```
research-assistant/
├── scripts/
│   ├── pdf_to_markdown.py     # PDF to Markdown converter
│   └── pdf_to_png.py         # PDF to PNG images converter
├── sources_pdf/       # Store original PDF papers
│   └── README.md     # Instructions for PDF storage
├── sources_markdown/  # Converted markdown versions
│   └── README.md     # Instructions for markdown files
└── sources_png/      # Extracted PNG images (300 DPI)
```

## Features

- Simple PDF to Markdown conversion
- High-quality PNG extraction (300 DPI)
- Maintains document structure with page numbers
- Batch processing support for multiple PDFs
- Clean, readable markdown output
- Organized file storage structure

## Requirements

- Python 3.8+
- Required Python packages (see requirements.txt):
  - PyMuPDF (for PDF processing)
  - tqdm (for progress tracking)
  - pandoc (for document conversion)
  - python-docx (for Word document handling)

## Usage Examples

### Convert a Single PDF to Markdown
```bash
python scripts/pdf_to_markdown.py sources_pdf/document.pdf -o sources_markdown/document.md
```

### Convert a Single PDF to PNG Images
```bash
python scripts/pdf_to_png.py sources_pdf/document.pdf -o sources_png/document/
```

### Convert All PDFs in Directory
```bash
# Using shell commands
for pdf in sources_pdf/*.pdf; do
    filename=$(basename "$pdf" .pdf)
    # To markdown
    python scripts/pdf_to_markdown.py "$pdf" -o "sources_markdown/$filename.md"
    # To PNG
    python scripts/pdf_to_png.py "$pdf" -o "sources_png/$filename"
done
```

### Python API Usage
```python
# For Markdown conversion
from scripts.pdf_to_markdown import PDFToMarkdown
converter = PDFToMarkdown()
result = converter.convert(
    "sources_pdf/document.pdf",
    "sources_markdown/document.md"
)
print(f"Converted {result.page_count} pages")

# For PNG conversion
from scripts.pdf_to_png import PDFToPNG
converter = PDFToPNG()
result = converter.convert(
    "sources_pdf/document.pdf",
    "sources_png/document"
)
print(f"Converted {result.page_count} pages to {result.output_directory}")
```

## Contributing

Feel free to:
- Submit issues for suggestions
- Create pull requests with improvements
- Share your customized versions
- Report any bugs or unclear documentation

## License

This project is licensed under MIT License - see the LICENSE file for details.
