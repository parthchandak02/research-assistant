# Research Assistant

A tool for managing academic research materials, including PDF processing, markdown conversion, and image extraction.

## Project Structure

```
research-assistant/
├── sources_pdf/       # Store original PDF papers
├── sources_markdown/  # Converted markdown versions of papers
├── sources_png/       # Extracted images from PDFs
├── scripts/          # Python scripts for conversion
└── draft.md          # Main literature review draft
```

## Features

- PDF to Markdown conversion with page tracking
- Image extraction from PDFs (300 DPI)
- Organized storage of research materials
- Literature review management
- Cross-referenced markdown and PNG files

## Requirements

- Python 3.8+
- Required Python packages (install via `pip install -r requirements.txt`):
  - pypdf==3.17.1
  - PyMuPDF==1.23.7
  - tqdm==4.66.1

## Setup

1. Clone the repository:
```bash
git clone https://github.com/parthchandak02/research-assistant.git
cd research-assistant
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Place your PDF files in the `sources_pdf` directory

## Usage

### Converting PDFs to Markdown and Images

1. Place your PDF files in the `sources_pdf` directory

2. Run the PNG extraction script:
```bash
python scripts/pdf_to_png.py
```
This will:
- Create PNG images for each page of each PDF
- Save them in `sources_png/<pdf_name>/page_XXX.png`
- Use 300 DPI for high-quality images

3. Run the Markdown conversion script:
```bash
python scripts/pdf_to_markdown.py
```
This will:
- Convert each PDF to a markdown file
- Include metadata (title, authors, etc.)
- Add page numbers and links to corresponding PNG files
- Save in `sources_markdown/<pdf_name>.md`

### Working with the Generated Files

- Each markdown file will contain links to its corresponding PNG files
- Page numbers in markdown files match the PNG file names
- Example link in markdown: `[View page image](../sources_png/paper_name/page_001.png)`

### Literature Review

- Use `draft.md` for your main literature review
- Reference the converted markdown files and images as needed
- Keep track of sources in the bibliography section

## Contributing

Feel free to submit issues and enhancement requests!

## License

MIT License - See LICENSE file for details
