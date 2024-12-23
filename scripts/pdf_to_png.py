#!/usr/bin/env python3

import fitz  # PyMuPDF
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
    """Result of a PDF to PNG conversion."""
    page_count: int
    source_path: Path
    output_directory: Path

class PDFToPNG:
    """Convert PDF files to PNG images."""

    def __init__(self):
        """Initialize the converter."""
        self.logger = logger

    def convert(self, input_path: Union[str, Path], output_dir: Optional[Union[str, Path]] = None) -> ConversionResult:
        """
        Convert a PDF file to PNG images.

        Args:
            input_path: Path to the PDF file
            output_dir: Optional path to save PNG files. If not provided, uses sources_png/pdf_name/

        Returns:
            ConversionResult object containing conversion metadata
        """
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"PDF file not found: {input_path}")

        # Set up output directory
        if output_dir is None:
            output_dir = Path('sources_png') / input_path.stem
        else:
            output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Processing PDF: {input_path.name}")

        # Open the PDF
        doc = fitz.open(input_path)
        total_pages = len(doc)
        self.logger.info(f"Total pages: {total_pages}")

        # Convert each page
        for page_num in range(total_pages):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))  # 300 DPI
            output_path = output_dir / f"page_{page_num + 1:03d}.png"
            pix.save(str(output_path))
            self.logger.info(f"Saved page {page_num + 1} to {output_path}")

        return ConversionResult(
            page_count=total_pages,
            source_path=input_path,
            output_directory=output_dir
        )

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Convert PDF to PNG images')
    parser.add_argument('input_path', type=str, help='Path to the PDF file')
    parser.add_argument('-o', '--output', type=str, help='Output directory for PNG files')

    args = parser.parse_args()

    converter = PDFToPNG()
    try:
        result = converter.convert(args.input_path, args.output)
        logger.info(f"Successfully converted {result.page_count} pages to {result.output_directory}")
    except Exception as e:
        logger.error(f"Error converting PDF: {e}")
        exit(1)

if __name__ == "__main__":
    main()
