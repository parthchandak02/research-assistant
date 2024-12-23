# Research Assistant

A tool for managing academic research materials, including PDF processing and document conversion for literature reviews and research papers.

## Quick Start

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
python scripts/pdf_to_markdown.py sources_pdf/paper.pdf -o sources_markdown/paper.md

# To PNG images (300 DPI)
python scripts/pdf_to_png.py sources_pdf/paper.pdf -o sources_png/paper/
```

## Project Structure

```
research-assistant/
├── scripts/              # Conversion tools
├── sources_pdf/          # Original PDF papers
├── sources_markdown/     # Converted markdown files
├── sources_png/          # Extracted images (300 DPI)
└── user_illustrations/   # Custom illustrations
```

## Features

- PDF to Markdown conversion with structure preservation
- High-quality PNG extraction (300 DPI)
- Batch processing support
- Clean, readable output
- Organized file management

## Requirements

- Python 3.8+
- Required packages (see requirements.txt):
  - PyMuPDF (PDF processing)
  - tqdm (progress tracking)
  - pandoc (document conversion)
  - python-docx (Word handling)

## Contributing

Feel free to submit issues, create pull requests, or share your customized versions.

## License

MIT License - see the LICENSE file for details.
