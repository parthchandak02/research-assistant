#!/usr/bin/env python3

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import logfire
import argparse
import time
from typing import List, Optional
import logging

# Import our PDF processing scripts
from scripts.pdf_analyze import PDFAnalyzer
from scripts.pdf_to_markdown import PDFToMarkdown
from scripts.pdf_to_png import PDFToPNG

# Configure logging
logfire.configure(
    service_name="research-assistant",
    environment=os.getenv('ENVIRONMENT', 'development'),
    send_to_logfire='if-token-present',
    console={"span_style": "simple"}
)

# Also set up basic Python logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ResearchAssistant:
    """Main class to handle all PDF processing workflows."""

    def __init__(self):
        """Initialize the research assistant."""
        self.source_dir = Path("sources_pdf")
        self.markdown_dir = Path("sources_markdown")
        self.png_dir = Path("sources_png")
        self.analysis_dir = Path("sources_analysis")

        # Create necessary directories
        for directory in [self.source_dir, self.markdown_dir, self.png_dir, self.analysis_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        # Load environment variables
        load_dotenv()

        # Get API key from environment
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set. Please check your .env file.")

        # Initialize processors
        self.analyzer = PDFAnalyzer(self.gemini_api_key)
        self.markdown_converter = PDFToMarkdown()
        self.png_converter = PDFToPNG()

    def get_pdf_files(self) -> List[Path]:
        """Get list of PDF files to process, excluding .gitkeep."""
        return [f for f in self.source_dir.glob("*.pdf") if f.name != '.gitkeep']

    async def process_single_pdf(self, pdf_path: Path):
        """Process a single PDF file through all converters."""
        try:
            logfire.info(f"Starting processing of {pdf_path.name}")

            # 1. Analyze PDF
            logfire.info(f"Analyzing {pdf_path.name}...")
            analysis_result = self.analyzer.analyze_single_pdf(pdf_path)
            if analysis_result:
                logfire.info(f"Analysis completed for {pdf_path.name}")
                # Get the new file path after potential renaming
                new_pdf_path = next(self.source_dir.glob(f"{pdf_path.stem}*.pdf"), pdf_path)
                if new_pdf_path != pdf_path:
                    logfire.info(f"Using renamed file: {new_pdf_path.name}")
                    pdf_path = new_pdf_path
            else:
                logfire.error(f"Analysis failed for {pdf_path.name}")
                return

            # 2. Convert to Markdown
            logfire.info(f"Converting {pdf_path.name} to Markdown...")
            md_result = self.markdown_converter.convert(
                pdf_path,
                self.markdown_dir / f"{pdf_path.stem}.md"
            )
            if md_result:
                logfire.info(f"Markdown conversion completed for {pdf_path.name}")
            else:
                logfire.error(f"Markdown conversion failed for {pdf_path.name}")

            # 3. Convert to PNG
            logfire.info(f"Converting {pdf_path.name} to PNG...")
            png_result = self.png_converter.convert(pdf_path)
            if png_result:
                logfire.info(f"PNG conversion completed for {pdf_path.name}")
            else:
                logfire.error(f"PNG conversion failed for {pdf_path.name}")

            logfire.info(f"Completed processing of {pdf_path.name}")

        except Exception as e:
            logfire.error(f"Error processing {pdf_path.name}: {e}")
            raise

    async def process_all_pdfs(self):
        """Process all PDFs in the source directory."""
        pdf_files = self.get_pdf_files()
        if not pdf_files:
            logfire.warning("No PDF files found in sources_pdf directory")
            return

        logfire.info(f"Found {len(pdf_files)} PDF files to process")

        for i, pdf_path in enumerate(pdf_files):
            try:
                # Check if analysis already exists
                analysis_exists = any(self.analysis_dir.glob(f"{pdf_path.stem}*_analysis.xml"))
                if analysis_exists:
                    logfire.info(f"Skipping {pdf_path.name} - analysis already exists")
                    continue

                # Add delay between files to avoid rate limiting
                if i > 0:
                    delay = 15  # 15 seconds delay between files
                    logfire.info(f"Waiting {delay} seconds before processing next file...")
                    await asyncio.sleep(delay)

                await self.process_single_pdf(pdf_path)

            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    wait_time = 300  # 5 minutes if we hit quota limit
                    logfire.warning(f"Hit API quota limit. Waiting {wait_time} seconds before retrying...")
                    await asyncio.sleep(wait_time)
                    # Retry this file
                    await self.process_single_pdf(pdf_path)
                else:
                    logfire.error(f"Error processing {pdf_path.name}: {e}")
                    continue

    def list_available_pdfs(self):
        """List all available PDFs in the source directory."""
        pdf_files = self.get_pdf_files()
        if not pdf_files:
            print("No PDF files found in sources_pdf directory")
        else:
            print("\nAvailable PDF files:")
            for i, pdf in enumerate(pdf_files, 1):
                print(f"{i}. {pdf.name}")

async def main():
    """Main entry point for the research assistant."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Research Assistant - PDF Processing Workflow')
    parser.add_argument('--file', '-f', help='Specific PDF file to process (must be in sources_pdf/)')
    parser.add_argument('--list', '-l', action='store_true', help='List available PDF files')
    args = parser.parse_args()

    # Initialize research assistant
    assistant = ResearchAssistant()

    try:
        if args.list:
            assistant.list_available_pdfs()
            return

        if args.file:
            # Process specific file
            pdf_path = assistant.source_dir / args.file
            if not pdf_path.exists():
                logfire.error(f"PDF file not found: {pdf_path}")
                return
            await assistant.process_single_pdf(pdf_path)
        else:
            # Process all files
            await assistant.process_all_pdfs()

    except Exception as e:
        logfire.error(f"Error in main process: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
