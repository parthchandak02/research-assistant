# Healthcare Education Technology Research Assistant

A systematic review project analyzing User-Centered Design (UCD) and Rapid Prototyping (RP) in healthcare educational technologies for youth.

## Project Overview
This research assistant helps manage and format systematic review documentation, ensuring consistent academic writing standards and proper citation management.

## Project Structure
1. Source PDFs stored in `sources_pdf/`
2. Markdown conversions in `sources_markdown/`
3. PNG extractions in `sources_png/`
4. Draft documents in root directory
5. Scripts for file processing in `scripts/`

## Setup & Installation

### Prerequisites
- Pandoc (for document conversion)
- Python 3.8+
- Git

### Installation
1. Install Pandoc:
   ```bash
   # macOS
   brew install pandoc

   # Ubuntu/Debian
   sudo apt-get install pandoc
   ```

2. Clone the repository:
   ```bash
   git clone [repository-url]
   cd research-assistant
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Document Conversion
Convert markdown drafts to Word format:
```bash
./scripts/convert_to_docx.sh
```

### File Processing
Process new source PDFs:
```bash
./scripts/process_pdfs.sh
```

## Documentation
- For detailed formatting guidelines and markdown standards, refer to `.cursorrules`
- Script documentation available in `scripts/README.md`
- Example templates in `templates/`

## Contributing
Please ensure all contributions follow the formatting guidelines in `.cursorrules` and maintain consistent academic writing standards.

## License
[Add appropriate license information]
