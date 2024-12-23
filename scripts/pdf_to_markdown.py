#!/usr/bin/env python3

import fitz
from pathlib import Path
import logging
from typing import Optional, Union
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ConversionResult:
    """Result of a PDF to Markdown conversion."""
    text_content: str
    page_count: int
    source_path: Path

class PDFToMarkdown:
    """Convert PDF files to Markdown format."""

    def __init__(self):
        """Initialize the converter."""
        self.logger = logger

    def convert(self, input_path: Union[str, Path], output_path: Optional[Union[str, Path]] = None) -> ConversionResult:
        """
        Convert a PDF file to markdown format.

        Args:
            input_path: Path to the PDF file
            output_path: Optional path to save the markdown file. If not provided, only returns the content.

        Returns:
            ConversionResult object containing the converted text and metadata
        """
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"PDF file not found: {input_path}")

        self.logger.info(f"Processing PDF: {input_path.name}")

        # Open the PDF
        doc = fitz.open(input_path)
        total_pages = len(doc)
        self.logger.info(f"Total pages: {total_pages}")

        # Convert content
        content = []
        for page_num, page in enumerate(doc, 1):
            text = page.get_text()
            if text.strip():
                content.append(f"## Page {page_num}\n\n{text}\n")

        markdown_content = "\n---\n".join(content)

        # Save to file if output path is provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(markdown_content, encoding='utf-8')
            self.logger.info(f"Saved markdown to: {output_path}")

        return ConversionResult(
            text_content=markdown_content,
            page_count=total_pages,
            source_path=input_path
        )

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Convert PDF to Markdown')
    parser.add_argument('input_path', type=str, help='Path to the PDF file')
    parser.add_argument('-o', '--output', type=str, help='Output markdown file path')

    args = parser.parse_args()

    converter = PDFToMarkdown()
    try:
        result = converter.convert(args.input_path, args.output)
        if not args.output:
            print(result.text_content)
    except Exception as e:
        logger.error(f"Error converting PDF: {e}")
        exit(1)

if __name__ == "__main__":
    main()
