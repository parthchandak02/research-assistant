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

    async def process_single_pdf(self, pdf_path: Path, skip_analysis: bool = False):
        """Process a single PDF file through all converters."""
        try:
            logfire.info(f"Starting processing of {pdf_path.name}")

            if not skip_analysis:
                # Clean up filename if needed - remove problematic characters
                clean_name = pdf_path.name
                if len(clean_name) > 100:  # Truncate very long names
                    clean_name = clean_name[:90] + "..." + pdf_path.suffix
                    new_path = pdf_path.parent / clean_name
                    try:
                        pdf_path.rename(new_path)
                        pdf_path = new_path
                        logfire.info(f"Renamed long filename to: {clean_name}")
                    except Exception as e:
                        logfire.warning(f"Could not rename file: {e}")

                # 1. Analyze PDF
                logfire.info(f"Analyzing {pdf_path.name}...")
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        analysis_result = self.analyzer.analyze_single_pdf(pdf_path)
                        if analysis_result:
                            logfire.info(f"Analysis completed for {pdf_path.name}")
                            # Get the new file path after potential renaming
                            new_pdf_path = next(self.source_dir.glob(f"{pdf_path.stem}*.pdf"), pdf_path)
                            if new_pdf_path != pdf_path:
                                logfire.info(f"File was renamed during analysis to: {new_pdf_path.name}")
                                pdf_path = new_pdf_path
                            break
                        else:
                            logfire.error(f"Analysis failed for {pdf_path.name}")
                            if attempt < max_retries - 1:
                                wait_time = (attempt + 1) * 30  # Exponential backoff
                                logfire.info(f"Retrying analysis in {wait_time} seconds...")
                                await asyncio.sleep(wait_time)
                            else:
                                return
                    except Exception as e:
                        if attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 30
                            logfire.warning(f"Analysis attempt {attempt + 1} failed: {e}. Retrying in {wait_time} seconds...")
                            await asyncio.sleep(wait_time)
                        else:
                            raise

            # Verify file exists before continuing
            if not pdf_path.exists():
                logfire.error(f"PDF file not found: {pdf_path}")
                return

            # Check what needs to be processed
            markdown_exists = (self.markdown_dir / f"{pdf_path.stem}.md").exists()
            png_dir_exists = (self.png_dir / pdf_path.stem).exists() and any((self.png_dir / pdf_path.stem).glob("*.png"))

            max_retries = 3
            # 2. Convert to Markdown if needed
            if not markdown_exists:
                logfire.info(f"Converting {pdf_path.name} to Markdown...")
                for attempt in range(max_retries):
                    try:
                        md_result = self.markdown_converter.convert(
                            pdf_path,
                            self.markdown_dir / f"{pdf_path.stem}.md"
                        )
                        if md_result:
                            logfire.info(f"✅ Markdown conversion completed for {pdf_path.name}")
                            break
                        else:
                            if attempt < max_retries - 1:
                                wait_time = (attempt + 1) * 10
                                logfire.info(f"Retrying markdown conversion in {wait_time} seconds...")
                                await asyncio.sleep(wait_time)
                            else:
                                logfire.error(f"❌ Markdown conversion failed for {pdf_path.name} after {max_retries} attempts")
                    except Exception as e:
                        if attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 10
                            logfire.warning(f"Markdown conversion attempt {attempt + 1} failed: {e}. Retrying in {wait_time} seconds...")
                            await asyncio.sleep(wait_time)
                        else:
                            logfire.error(f"❌ Markdown conversion failed: {e}")

            # 3. Convert to PNG if needed
            if not png_dir_exists:
                logfire.info(f"Converting {pdf_path.name} to PNG...")
                for attempt in range(max_retries):
                    try:
                        png_result = self.png_converter.convert(pdf_path)
                        if png_result:
                            logfire.info(f"✅ PNG conversion completed for {pdf_path.name}")
                            break
                        else:
                            if attempt < max_retries - 1:
                                wait_time = (attempt + 1) * 10
                                logfire.info(f"Retrying PNG conversion in {wait_time} seconds...")
                                await asyncio.sleep(wait_time)
                            else:
                                logfire.error(f"❌ PNG conversion failed for {pdf_path.name} after {max_retries} attempts")
                    except Exception as e:
                        if attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 10
                            logfire.warning(f"PNG conversion attempt {attempt + 1} failed: {e}. Retrying in {wait_time} seconds...")
                            await asyncio.sleep(wait_time)
                        else:
                            logfire.error(f"❌ PNG conversion failed: {e}")

            logfire.info(f"✨ Completed processing of {pdf_path.name}")

        except Exception as e:
            logfire.error(f"❌ Error processing {pdf_path.name}: {e}")
            raise

    def check_processing_status(self):
        """Check the status of all files and their processing outputs."""
        pdf_files = self.get_pdf_files()
        if not pdf_files:
            logfire.warning("📂 No PDF files found in sources_pdf directory")
            return

        total_files = len(pdf_files)
        complete_files = 0
        incomplete_files = []

        logfire.info(f"\n📊 Processing Status Report for {total_files} files:")
        print("\n" + "="*50)

        for pdf_path in pdf_files:
            analysis_exists = any(self.analysis_dir.glob(f"{pdf_path.stem}*_analysis.xml"))
            markdown_exists = (self.markdown_dir / f"{pdf_path.stem}.md").exists()
            png_dir_exists = (self.png_dir / pdf_path.stem).exists() and any((self.png_dir / pdf_path.stem).glob("*.png"))

            status = []
            if analysis_exists:
                status.append("✅ Analysis")
            else:
                status.append("❌ Analysis")

            if markdown_exists:
                status.append("✅ Markdown")
            else:
                status.append("❌ Markdown")

            if png_dir_exists:
                status.append("✅ PNG")
            else:
                status.append("❌ PNG")

            if all([analysis_exists, markdown_exists, png_dir_exists]):
                complete_files += 1
                print(f"✨ {pdf_path.name}:")
            else:
                incomplete_files.append(pdf_path.name)
                print(f"⚠️  {pdf_path.name}:")

            print("   " + " | ".join(status))

        print("\n" + "="*50)
        print(f"📈 Summary:")
        print(f"   ✅ Complete: {complete_files}/{total_files} files")
        if incomplete_files:
            print(f"   ⚠️  Incomplete: {len(incomplete_files)}/{total_files} files")
            print("   Files needing attention:")
            for file in incomplete_files:
                print(f"   - {file}")
        else:
            print("   🎉 All files completely processed!")
        print("="*50 + "\n")

    async def process_all_pdfs(self):
        """Process all PDFs in the source directory."""
        pdf_files = self.get_pdf_files()
        if not pdf_files:
            logfire.warning("No PDF files found in sources_pdf directory")
            return

        logfire.info(f"Found {len(pdf_files)} PDF files to process")

        for i, pdf_path in enumerate(pdf_files):
            try:
                # Check if all outputs exist
                analysis_exists = any(self.analysis_dir.glob(f"{pdf_path.stem}*_analysis.xml"))
                markdown_exists = (self.markdown_dir / f"{pdf_path.stem}.md").exists()
                png_dir_exists = (self.png_dir / pdf_path.stem).exists() and any((self.png_dir / pdf_path.stem).glob("*.png"))

                if analysis_exists and markdown_exists and png_dir_exists:
                    logfire.info(f"✅ Skipping {pdf_path.name} - all outputs exist")
                    continue
                else:
                    # Log what's missing
                    if not analysis_exists:
                        logfire.info(f"❌ Analysis missing for {pdf_path.name}")
                    if not markdown_exists:
                        logfire.info(f"❌ Markdown missing for {pdf_path.name}")
                    if not png_dir_exists:
                        logfire.info(f"❌ PNG files missing for {pdf_path.name}")

                # Add delay between files to avoid rate limiting
                if i > 0:
                    delay = 15  # 15 seconds delay between files
                    logfire.info(f"⏳ Waiting {delay} seconds before processing next file...")
                    await asyncio.sleep(delay)

                # Skip analysis if it exists
                await self.process_single_pdf(pdf_path, skip_analysis=analysis_exists)

            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    wait_time = 300  # 5 minutes if we hit quota limit
                    logfire.warning(f"⚠️  Hit API quota limit. Waiting {wait_time} seconds before retrying...")
                    await asyncio.sleep(wait_time)
                    # Retry this file
                    await self.process_single_pdf(pdf_path, skip_analysis=analysis_exists)
                else:
                    logfire.error(f"❌ Error processing {pdf_path.name}: {e}")
                    continue

        # Run final status check
        self.check_processing_status()

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
