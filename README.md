# Research Assistant

A tool for managing academic research materials, including PDF processing, markdown conversion, and image extraction.

## Project Structure

```
research-assistant/
├── pdf_sources/       # Store original PDF papers
├── markdown_sources/  # Converted markdown versions of papers
├── image_sources/     # Extracted images from PDFs
├── scripts/          # Python scripts for conversion
└── draft.md          # Main literature review draft
```

## Features

- PDF to Markdown conversion
- Image extraction from PDFs
- Organized storage of research materials
- Literature review management

## Requirements

- Python 3.8+
- Required Python packages:
  - pdf2image
  - pytesseract
  - pypdf2
  - pillow

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/research-assistant.git
cd research-assistant
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Place your PDF files in the `pdf_sources` directory

4. Run the conversion scripts:
```bash
python scripts/pdf_to_markdown.py
python scripts/extract_images.py
```

## Usage

1. Add PDF papers to `pdf_sources/`
2. Run the conversion scripts
3. Find converted markdown files in `markdown_sources/`
4. Find extracted images in `image_sources/`
5. Update `draft.md` with your literature review

## Contributing

Feel free to submit issues and enhancement requests!

## License

MIT License - See LICENSE file for details
