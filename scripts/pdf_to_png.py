#!/usr/bin/env python3

import os
import logging
from pathlib import Path
import fitz  # PyMuPDF
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pdf_to_png_conversion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_output_directory(output_base_dir: str) -> None:
    """Create output directory if it doesn't exist."""
    try:
        os.makedirs(output_base_dir, exist_ok=True)
        logger.info(f"Output directory setup complete: {output_base_dir}")
    except Exception as e:
        logger.error(f"Failed to create output directory: {e}")
        raise

def get_safe_filename(filename: str) -> str:
    """Convert filename to a safe version by removing problematic characters."""
    return "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_')).rstrip()

def convert_pdf_to_png(pdf_path: str, output_dir: str) -> None:
    """Convert a single PDF file to PNG images."""
    try:
        # Create subfolder for this PDF's images
        pdf_name = get_safe_filename(Path(pdf_path).stem)
        pdf_output_dir = os.path.join(output_dir, pdf_name)
        os.makedirs(pdf_output_dir, exist_ok=True)
        
        # Open PDF
        doc = fitz.open(pdf_path)
        logger.info(f"Processing PDF: {pdf_path} ({len(doc)} pages)")
        
        # Convert each page with progress bar
        for page_num in tqdm(range(len(doc)), desc=f"Converting {pdf_name}", unit="page"):
            page = doc[page_num]
            
            # Get the page's image
            pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))  # 300 DPI
            
            # Save image
            output_path = os.path.join(pdf_output_dir, f"page_{page_num + 1:03d}.png")
            pix.save(output_path)
            
        logger.info(f"Successfully converted {pdf_path} to PNGs")
        doc.close()
        
    except Exception as e:
        logger.error(f"Error converting {pdf_path}: {e}")
        raise

def main():
    """Main function to process all PDFs in the source directory."""
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    source_dir = project_root / "sources_pdf"
    output_dir = project_root / "sources_png"
    
    try:
        # Setup output directory
        setup_output_directory(output_dir)
        
        # Get list of PDF files
        pdf_files = [f for f in os.listdir(source_dir) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            logger.warning("No PDF files found in source directory")
            return
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        # Process each PDF
        for pdf_file in pdf_files:
            pdf_path = os.path.join(source_dir, pdf_file)
            convert_pdf_to_png(pdf_path, output_dir)
        
        logger.info("All PDF conversions completed successfully")
        
    except Exception as e:
        logger.error(f"An error occurred during processing: {e}")
        raise

if __name__ == "__main__":
    main()
