from __future__ import annotations

import asyncio
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional
import logfire
import os
from openai import AsyncOpenAI
from tqdm import tqdm
from pydantic_ai import Agent, RunContext
from dotenv import load_dotenv

# Add at the top of each agent file after imports
logfire.configure(
    service_name="research-assistant",
    service_version="1.0.0",
    environment="development",
    send_to_logfire='if-token-present',
    console={"span_style": "simple"}
)

# Configure logfire with simplified console settings
logfire.configure(
    service_name="research-assistant",
    service_version="1.0.0",
    environment="development",
    send_to_logfire='if-token-present',
    console={
        "span_style": "simple"
    }
)

# Change relative imports to absolute imports
import sys
sys.path.append(str(Path(__file__).parent.parent))
from scripts.pdf_to_markdown import convert_pdf_to_markdown
from scripts.pdf_to_png import convert_pdf_to_png

@dataclass
class ProcessingResult:
    markdown_path: Path
    image_paths: List[Path]

@dataclass
class ProcessorDeps:
    openai: Optional[AsyncOpenAI] = None

class DocumentProcessor:
    """Agent for processing PDF documents into markdown and images."""
    
    def __init__(self):
        self.agent = Agent(
            'openai:gpt-3.5-turbo',
            system_prompt=(
                "You are a document processing agent. Your job is to convert PDF "
                "documents into markdown and extract images."
            ),
            deps_type=ProcessorDeps
        )
        self.deps: Optional[ProcessorDeps] = None

    async def initialize(self, openai: Optional[AsyncOpenAI] = None):
        """Initialize the agent with OpenAI client."""
        self.deps = ProcessorDeps(openai=openai)

    async def process_pdf(self, pdf_path: Path) -> ProcessingResult:
        """Process a single PDF file into markdown and images."""
        with logfire.span('process_pdf', pdf_path=str(pdf_path)):
            # Create output directories
            markdown_dir = Path("sources_markdown")
            images_dir = Path("sources_png")
            markdown_dir.mkdir(parents=True, exist_ok=True)
            images_dir.mkdir(parents=True, exist_ok=True)
            
            # Convert PDF to markdown with advanced mode if OpenAI is available
            markdown_path = await convert_pdf_to_markdown(
                pdf_path,
                markdown_dir,
                advanced_mode=self.deps and self.deps.openai is not None,
                openai=self.deps.openai if self.deps else None
            )
            
            # Convert PDF to images
            convert_pdf_to_png(str(pdf_path), str(images_dir))
            # Get the list of generated images
            pdf_name = Path(pdf_path).stem
            image_dir = images_dir / pdf_name
            image_paths = list(image_dir.glob('*.png'))
            
            return ProcessingResult(
                markdown_path=markdown_path,
                image_paths=image_paths
            )
    
    async def process_directory(self, pdf_dir: Path, skip_existing: bool = True) -> List[ProcessingResult]:
        """Process all PDF files in a directory."""
        if not pdf_dir.exists():
            raise FileNotFoundError(f"Directory not found: {pdf_dir}")
        
        # Get all PDF files
        pdf_files = list(pdf_dir.glob('*.pdf'))
        if not pdf_files:
            logfire.warn(f"No PDF files found in {pdf_dir}")
            return []
        
        results = []
        with tqdm(total=len(pdf_files), desc="Processing PDFs") as pbar:
            for pdf_path in pdf_files:
                # Check if output already exists
                markdown_path = Path("sources_markdown") / f"{pdf_path.stem}.md"
                if skip_existing and markdown_path.exists():
                    logfire.info(f"Skipping {pdf_path.name} - already processed")
                    pbar.update(1)
                    continue
                
                try:
                    result = await self.process_pdf(pdf_path)
                    results.append(result)
                    logfire.info(f"Successfully processed {pdf_path.name}")
                except Exception as e:
                    logfire.error(f"Error processing {pdf_path.name}: {e}")
                
                pbar.update(1)
        
        return results

async def main():
    """Run the document processor as a standalone script."""
    load_dotenv()  # Load environment variables
    
    logfire.info("Starting document processor")
    
    # Initialize OpenAI client if API key is available
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        openai = AsyncOpenAI()
        logfire.info("OpenAI client initialized - using advanced mode")
    else:
        openai = None
        logfire.warn("No OpenAI API key found - using basic mode")
    
    # Initialize processor
    processor = DocumentProcessor()
    await processor.initialize(openai)
    logfire.info("Document processor initialized")
    
    import argparse
    parser = argparse.ArgumentParser(description='Process PDF documents into markdown and images')
    parser.add_argument('--input-dir', type=str, default='sources_pdf',
                      help='Input directory containing PDF files')
    parser.add_argument('--no-skip', action='store_true',
                      help='Do not skip already processed files')
    args = parser.parse_args()
    
    # Process all PDFs in directory
    input_dir = Path(args.input_dir)
    logfire.info(f"Processing PDFs from directory: {input_dir}")
    
    try:
        results = await processor.process_directory(input_dir, skip_existing=not args.no_skip)
        if results:
            logfire.info(f"Successfully processed {len(results)} PDF files")
            for result in results:
                logfire.info(f"Generated markdown: {result.markdown_path}")
                logfire.info(f"Generated {len(result.image_paths)} images")
        else:
            logfire.info("No new files were processed")
    except Exception as e:
        logfire.error(f"Error during batch processing: {e}", exc_info=True)

    logfire.info("Document processing completed")

if __name__ == "__main__":
    asyncio.run(main())
