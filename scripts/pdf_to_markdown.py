#!/usr/bin/env python3

import os
import fitz
from pathlib import Path
from typing import Optional, Dict
from dataclasses import dataclass
import asyncio
from openai import AsyncOpenAI
import logging
import json
from tqdm import tqdm
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pdf_to_markdown_conversion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class DocumentMetadata:
    title: str
    authors: list[str]
    year: Optional[int] = None
    doi: Optional[str] = None
    
    def to_apa_citation(self) -> str:
        authors_text = ""
        if self.authors:
            if len(self.authors) == 1:
                authors_text = f"{self.authors[0]}"
            elif len(self.authors) == 2:
                authors_text = f"{self.authors[0]} & {self.authors[1]}"
            else:
                authors_text = f"{self.authors[0]} et al."
        
        year_text = f"({self.year})" if self.year else ""
        return f"{authors_text}{year_text}"

async def extract_metadata(openai: AsyncOpenAI, first_page_text: str) -> DocumentMetadata:
    """Extract metadata from the first page using OpenAI."""
    prompt = f"""Extract the following information from this academic paper text:
1. Title
2. Authors (as a list)
3. Year
4. DOI (if present)

Text:
{first_page_text[:2000]}  # First 2000 chars should be enough for metadata

Return the information in this exact format (including the quotes and brackets):
{{
    "title": "paper title here",
    "authors": ["Author 1", "Author 2"],
    "year": YYYY,  # or null if not found
    "doi": "doi string here"  # or null if not found
}}"""

    response = await openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that extracts metadata from academic papers. Return only valid JSON."},
            {"role": "user", "content": prompt}
        ]
    )
    
    try:
        result = json.loads(response.choices[0].message.content)
        return DocumentMetadata(**result)
    except Exception as e:
        print(f"Error parsing metadata: {e}")
        return DocumentMetadata(title="Unknown", authors=[], year=None)

async def convert_pdf_to_markdown(
    pdf_path: Path,
    output_dir: Path,
    advanced_mode: bool = False,
    openai: Optional[AsyncOpenAI] = None
) -> Path:
    """Convert PDF to markdown with optional metadata extraction and citations."""
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    logger.info(f"Processing PDF: {pdf_path.name}")
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Open the PDF
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    logger.info(f"Total pages: {total_pages}")
    
    # Extract metadata if in advanced mode
    metadata = None
    if advanced_mode and openai:
        logger.info("Extracting metadata using OpenAI...")
        first_page = doc[0].get_text()
        metadata = await extract_metadata(openai, first_page)
        logger.info(f"Extracted metadata: {metadata}")
    
    # Create markdown file
    markdown_path = output_dir / f"{pdf_path.stem}.md"
    logger.info(f"Creating markdown file: {markdown_path}")
    
    with open(markdown_path, 'w', encoding='utf-8') as md_file:
        # Write metadata if available
        if metadata:
            md_file.write(f"# {metadata.title}\n\n")
            if metadata.authors:
                md_file.write("## Authors\n")
                for author in metadata.authors:
                    md_file.write(f"- {author}\n")
                md_file.write("\n")
        
        # Process each page with progress bar
        with tqdm(total=total_pages, desc="Converting pages") as pbar:
            for page_num, page in enumerate(doc):
                text = page.get_text()
                if text.strip():
                    # Add page citation if in advanced mode
                    if advanced_mode and metadata:
                        citation = f"\n\n[{metadata.to_apa_citation()}, p. {page_num + 1}]\n\n"
                        md_file.write(citation)
                    
                    md_file.write(text)
                    md_file.write("\n\n---\n\n")  # Page separator
                
                pbar.update(1)
                time.sleep(0.1)  # Small delay to make progress visible
    
    logger.info(f"Successfully created markdown file: {markdown_path}")
    return markdown_path

async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Convert PDF to Markdown')
    parser.add_argument('pdf_path', type=str, help='Path to the PDF file')
    parser.add_argument('--output-dir', type=str, default='sources_markdown',
                      help='Output directory for markdown files')
    parser.add_argument('--advanced', action='store_true',
                      help='Enable advanced mode with OpenAI metadata extraction')
    
    args = parser.parse_args()
    
    pdf_path = Path(args.pdf_path)
    output_dir = Path(args.output_dir)
    
    openai = None
    if args.advanced:
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OPENAI_API_KEY environment variable is required for advanced mode")
        openai = AsyncOpenAI()
    
    try:
        markdown_path = await convert_pdf_to_markdown(
            pdf_path,
            output_dir,
            advanced_mode=args.advanced,
            openai=openai
        )
        logger.info(f"Successfully converted {pdf_path} to {markdown_path}")
    except Exception as e:
        logger.error(f"Error converting PDF: {e}")

if __name__ == "__main__":
    asyncio.run(main())
